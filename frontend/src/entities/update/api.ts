import { invoke } from '@tauri-apps/api/core'

import type {
  UpdateCheckResult,
  UpdateDownloadResult,
  UpdateInstallResult,
} from './types'

/**
 * Primary manifest URL for production updates.
 * Hosted on the zhangshu.xin domain.
 */
export const PRIMARY_MANIFEST_URL =
  'https://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json'

/**
 * Fallback manifest URL for production updates.
 * Hosted on the legacy emailbs.xin domain as a backup.
 */
export const FALLBACK_MANIFEST_URL =
  'https://updates.emailbs.xin/zhangshu/stable/windows-x64/latest.json'

/** All manifest URLs in priority order. */
export const DEFAULT_MANIFEST_URLS: readonly string[] = [
  PRIMARY_MANIFEST_URL,
  FALLBACK_MANIFEST_URL,
] as const

/** Check for updates by fetching and parsing the release manifest. */
export function checkForUpdate(
  manifestUrl?: string,
  channel?: string,
): Promise<UpdateCheckResult> {
  return invoke<UpdateCheckResult>('check_update', {
    manifestUrl: manifestUrl ?? PRIMARY_MANIFEST_URL,
    channel: channel ?? null,
  })
}

/**
 * Check for updates with fallback: tries the primary URL first, then the
 * fallback URL if the primary fails. If the primary succeeds (even with
 * "no update"), the fallback is not attempted.
 *
 * Returns the check result with the activeManifestUrl field set to whichever
 * URL succeeded, so that the download phase can use the same source.
 */
export async function checkForUpdateWithFallback(
  channel?: string,
): Promise<UpdateCheckResult & { activeManifestUrl: string | null }> {
  const errors: string[] = []

  for (const url of DEFAULT_MANIFEST_URLS) {
    try {
      const result = await checkForUpdate(url, channel)
      if (result.error) {
        errors.push(result.error)
        continue
      }
      return { ...result, activeManifestUrl: url }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      errors.push(msg)
    }
  }

  // Both URLs failed
  const detail = errors
    .filter(Boolean)
    .map((msg, index) => `源${index + 1}: ${msg}`)
    .join('；')

  return {
    hasUpdate: false,
    currentVersion: '',
    latestVersion: '',
    manifest: null,
    error: detail
      ? `主用与备用更新源均不可用。${detail}`
      : '主用与备用更新源均不可用，请检查网络连接后重试',
    requiresManualDownload: false,
    activeManifestUrl: null,
  }
}

/** Download the installer for the given version after verifying the manifest. */
export function downloadUpdate(
  manifestUrl: string,
  expectedVersion: string,
): Promise<UpdateDownloadResult> {
  return invoke<UpdateDownloadResult>('download_update', {
    manifestUrl,
    expectedVersion,
  })
}

/** Launch the updater helper to install a previously verified update. */
export function installUpdate(
  expectedVersion: string,
): Promise<UpdateInstallResult> {
  return invoke<UpdateInstallResult>('install_update', {
    expectedVersion,
  })
}
