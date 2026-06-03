/** Installer metadata from the release manifest. */
export interface UpdateInstallerInfo {
  url: string
  sha256: string
  sizeBytes: number
}

/** Parsed release manifest from the update server. */
export interface UpdateManifest {
  schemaVersion: number
  channel: string
  platform: string
  arch: string
  version: string
  minSupportedVersion: string
  publishedAt: string
  installer: UpdateInstallerInfo
  releaseNotes: string[]
  critical: boolean
}

/** Result of checking for updates (returned by Rust check_update command). */
export interface UpdateCheckResult {
  hasUpdate: boolean
  currentVersion: string
  latestVersion: string
  manifest: UpdateManifest | null
  error: string | null
  /**
   * True when the current version is below the manifest's `minSupportedVersion`.
   * Auto-update is blocked; the user must download the installer manually.
   */
  requiresManualDownload: boolean
}

/** Download state reported by the Rust download_update command. */
export interface UpdateDownloadResult {
  success: boolean
  version: string
  cachedPath: string | null
  error: string | null
}

/** Install result from the Rust install_update command. */
export interface UpdateInstallResult {
  success: boolean
  error: string | null
}

/**
 * Aggregate UI state for the update panel.
 * The frontend tracks the full lifecycle from check → download → install.
 */
export type UpdatePhase =
  | 'idle'
  | 'checking'
  | 'upToDate'
  | 'available'
  | 'requiresManualUpdate'
  | 'downloading'
  | 'downloaded'
  | 'installing'
  | 'checkFailed'
  | 'downloadFailed'
  | 'installFailed'
