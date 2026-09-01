[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath,
    [Parameter(Mandatory = $true)]
    [string]$EvidenceDirectory,
    [Parameter(Mandatory = $true)]
    [string]$ExecutionAccount,
    [Parameter(Mandatory = $true)]
    [string]$ExecutionSid
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ApprovedAccount = $ExecutionAccount
$ApprovedSid = $ExecutionSid
$RequiredNames = @(
    'data_batch_1.bin',
    'data_batch_2.bin',
    'data_batch_3.bin',
    'data_batch_4.bin',
    'data_batch_5.bin',
    'test_batch.bin',
    'prepared-manifest.json'
)

function Resolve-ApprovedTarget {
    param([string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or $item.Name -cne 'cifar-10-batches-bin') {
        throw 'ACL target is not the approved prepared CIFAR directory.'
    }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'ACL target may not be a reparse point.'
    }
    $children = @(Get-ChildItem -LiteralPath $item.FullName -Force)
    if (@($children | Where-Object { $_.PSIsContainer }).Count -ne 0) {
        throw 'Prepared directory contains an unexpected child directory.'
    }
    $observed = @($children.Name | Sort-Object)
    $expected = @($RequiredNames | Sort-Object)
    if (Compare-Object -ReferenceObject $expected -DifferenceObject $observed) {
        throw 'Prepared directory member set differs from D-030.'
    }
    foreach ($child in $children) {
        if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Prepared member may not be a reparse point: $($child.Name)"
        }
    }
    return $item
}

function Get-AccessRecord {
    param([System.Security.AccessControl.FileSystemAccessRule]$Rule)
    $translatedSid = $Rule.IdentityReference.Translate(
        [System.Security.Principal.SecurityIdentifier]
    ).Value
    return [pscustomobject][ordered]@{
        identity = $Rule.IdentityReference.Value
        sid = $translatedSid
        access_control_type = $Rule.AccessControlType.ToString()
        rights = $Rule.FileSystemRights.ToString()
        rights_value = [int64]$Rule.FileSystemRights
        inheritance_flags = $Rule.InheritanceFlags.ToString()
        propagation_flags = $Rule.PropagationFlags.ToString()
        inherited = [bool]$Rule.IsInherited
    }
}

function Get-DescriptorRecord {
    param([System.IO.FileSystemInfo]$Item)
    $acl = Get-Acl -LiteralPath $Item.FullName
    $access = @(
        $acl.Access |
            ForEach-Object { Get-AccessRecord $_ } |
            Sort-Object sid, access_control_type, rights_value, inheritance_flags, propagation_flags, inherited
    )
    return [ordered]@{
        path = $Item.FullName
        owner = $acl.Owner
        protected = [bool]$acl.AreAccessRulesProtected
        sddl = $acl.Sddl
        access = $access
    }
}

function Get-Snapshot {
    param([System.IO.DirectoryInfo]$Target, [string]$Stage)
    $files = @()
    foreach ($name in $RequiredNames) {
        $path = Join-Path $Target.FullName $name
        $item = Get-Item -LiteralPath $path -Force
        $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName
        $files += [ordered]@{
            name = $name
            bytes = [int64]$item.Length
            sha256 = $hash.Hash.ToUpperInvariant()
        }
    }
    $descriptorItems = @($Target) + @(
        $RequiredNames | ForEach-Object {
            Get-Item -LiteralPath (Join-Path $Target.FullName $_) -Force
        }
    )
    return [ordered]@{
        classification = 'PHASE6-PREFLIGHT-ACL-CORRECTIVE-EVIDENCE-V1'
        evidence_class = 'DERIVED'
        stage = $Stage
        target = $Target.FullName
        current_account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        current_sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        files = $files
        descriptors = @($descriptorItems | ForEach-Object { Get-DescriptorRecord $_ })
        formal_optimizer_calls = 0
        data_bytes_changed = $false
    }
}

function Write-NewJson {
    param([string]$Path, [object]$Document)
    if (Test-Path -LiteralPath $Path) {
        throw "Evidence target already exists: $Path"
    }
    $json = $Document | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($Path, $json + "`n", [Text.UTF8Encoding]::new($false))
}

function Assert-FileIdentityEqual {
    param([object]$Before, [object]$After)
    $beforeJson = $Before.files | ConvertTo-Json -Depth 5 -Compress
    $afterJson = $After.files | ConvertTo-Json -Depth 5 -Compress
    if ($beforeJson -cne $afterJson) {
        throw 'Prepared file bytes/SHA256 changed during ACL correction.'
    }
}

function Assert-DescriptorDelta {
    param([object]$Before, [object]$After)
    $allowed = [int64]([System.Security.AccessControl.FileSystemRights]::ReadAndExecute -bor
        [System.Security.AccessControl.FileSystemRights]::Synchronize)
    for ($index = 0; $index -lt $Before.descriptors.Count; $index++) {
        $old = $Before.descriptors[$index]
        $new = $After.descriptors[$index]
        if ($old.path -cne $new.path -or $old.owner -cne $new.owner -or
            $old.protected -ne $new.protected) {
            throw 'ACL owner, target, or inheritance protection changed.'
        }
        $oldOther = @($old.access | Where-Object { $_.sid -cne $ApprovedSid } | ForEach-Object {
            '{0}|{1}|{2}|{3}|{4}|{5}' -f $_.sid, $_.access_control_type,
                ([int64]$_.rights_value), $_.inheritance_flags, $_.propagation_flags,
                ([bool]$_.inherited)
        } | Sort-Object)
        $newOther = @($new.access | Where-Object { $_.sid -cne $ApprovedSid } | ForEach-Object {
            '{0}|{1}|{2}|{3}|{4}|{5}' -f $_.sid, $_.access_control_type,
                ([int64]$_.rights_value), $_.inheritance_flags, $_.propagation_flags,
                ([bool]$_.inherited)
        } | Sort-Object)
        if (($oldOther | ConvertTo-Json -Compress) -cne
            ($newOther | ConvertTo-Json -Compress)) {
            throw 'A pre-existing non-target ACE changed.'
        }
        $oldTarget = @($old.access | Where-Object { $_.sid -ceq $ApprovedSid })
        if ($oldTarget.Count -ne 0) {
            throw 'Target account already had an ACE before the approved grant.'
        }
        $newTarget = @($new.access | Where-Object { $_.sid -ceq $ApprovedSid })
        if ($newTarget.Count -ne 1) {
            throw 'Target account did not receive exactly one read/traverse ACE.'
        }
        foreach ($ace in $newTarget) {
            if ($ace.access_control_type -cne 'Allow' -or
                (($ace.rights_value -band (-bnot $allowed)) -ne 0)) {
                throw 'Target account received rights broader than read/execute/synchronize.'
            }
        }
    }
}

$target = Resolve-ApprovedTarget $TargetPath
$evidence = [IO.Path]::GetFullPath($EvidenceDirectory)
[IO.Directory]::CreateDirectory($evidence) | Out-Null
$beforePath = Join-Path $evidence 'phase6_acl_before.json'
$afterPath = Join-Path $evidence 'phase6_acl_after.json'
$reportPath = Join-Path $evidence 'phase6_acl_corrective_report.json'
$failurePath = Join-Path $evidence 'phase6_acl_after_failure.json'
foreach ($path in @($beforePath, $afterPath, $reportPath, $failurePath)) {
    if (Test-Path -LiteralPath $path) {
        throw "ACL corrective evidence already exists: $path"
    }
}

$before = Get-Snapshot $target 'BEFORE'
if ($before.current_account -cne $before.descriptors[0].owner) {
    throw 'ACL correction must run as the existing directory owner.'
}
foreach ($descriptor in $before.descriptors) {
    if (@($descriptor.access | Where-Object { $_.sid -ceq $ApprovedSid }).Count -ne 0) {
        throw 'Approved account already has an ACE; additive correction is ambiguous.'
    }
}
Write-NewJson $beforePath $before

$rootAcl = Get-Acl -LiteralPath $target.FullName
$grantRights = [System.Security.AccessControl.FileSystemRights]::ReadAndExecute -bor
    [System.Security.AccessControl.FileSystemRights]::Synchronize
$grantRule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    [System.Security.Principal.SecurityIdentifier]::new($ApprovedSid),
    $grantRights,
    ([System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [System.Security.AccessControl.InheritanceFlags]::ObjectInherit),
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AccessControlType]::Allow
)
$rootAcl.AddAccessRule($grantRule) | Out-Null
try {
    Set-Acl -LiteralPath $target.FullName -AclObject $rootAcl
    $after = Get-Snapshot $target 'AFTER'
    Assert-FileIdentityEqual $before $after
    Assert-DescriptorDelta $before $after
} catch {
    if (-not (Test-Path -LiteralPath $failurePath)) {
        $failed = Get-Snapshot $target 'AFTER-FAILED-ACL-VALIDATION'
        Write-NewJson $failurePath $failed
    }
    throw
}
Write-NewJson $afterPath $after
$report = [ordered]@{
    classification = 'PHASE6-PREFLIGHT-ACL-CORRECTIVE-REPORT-V1'
    evidence_class = 'DERIVED'
    target = $target.FullName
    execution_account = $ApprovedAccount
    execution_sid = $ApprovedSid
    grant = '(OI)(CI)(RX)'
    owner_unchanged = $true
    inheritance_protection_unchanged = $true
    non_target_aces_unchanged = $true
    data_bytes_sha256_unchanged = $true
    write_modify_delete_ownership_acl_change_granted = $false
    formal_optimizer_calls = 0
}
Write-NewJson $reportPath $report
Get-FileHash -Algorithm SHA256 -LiteralPath $beforePath, $afterPath, $reportPath |
    Select-Object Path, Hash
