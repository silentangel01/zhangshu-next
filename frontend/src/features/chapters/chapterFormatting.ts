/**
 * Pure functions for chapter content formatting.
 * No DOM access, no API calls, no localStorage.
 */

export type FirstLineIndentSpaces = 0 | 2 | 4
export type ParagraphSpacingLines = 0 | 1 | 2

export interface ChapterFormatOptions {
  firstLineIndentSpaces: FirstLineIndentSpaces
  paragraphSpacingLines: ParagraphSpacingLines
}

export interface ChapterFormatResult {
  content: string
  changed: boolean
  paragraphCount: number
  changes: string[]
}

/**
 * Format chapter content according to the given rules.
 *
 * - Normalises line endings to LF.
 * - Strips trailing whitespace from every line.
 * - Strips existing leading whitespace (spaces, tabs, full-width spaces)
 *   from non-empty lines and re-applies the configured indent.
 * - Collapses runs of 3+ blank lines to the configured paragraph spacing.
 * - Inserts the configured number of blank lines between paragraphs.
 * - Trims leading/trailing blank lines from the whole document.
 * - Ensures at most one trailing newline at end of file.
 */
export function formatChapterContent(
  content: string,
  options: ChapterFormatOptions,
): ChapterFormatResult {
  const changes: string[] = []

  if (!content || content.trim() === '') {
    return { content: '', changed: content !== '', paragraphCount: 0, changes: [] }
  }

  // 1. Normalise line endings to LF
  let normalised = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n')

  // 2. Strip trailing whitespace per line
  normalised = normalised
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')

  // 3. Split into lines
  const lines = normalised.split('\n')

  // 4. Trim leading blank lines from the document
  let startIdx = 0
  while (startIdx < lines.length && lines[startIdx]!.trim() === '') {
    startIdx++
  }

  // 5. Trim trailing blank lines from the document
  let endIdx = lines.length - 1
  while (endIdx >= startIdx && lines[endIdx]!.trim() === '') {
    endIdx--
  }

  if (startIdx > endIdx) {
    return { content: '', changed: true, paragraphCount: 0, changes: ['清理空白内容'] }
  }

  const indent = options.firstLineIndentSpaces > 0
    ? ' '.repeat(options.firstLineIndentSpaces)
    : ''

  const result: string[] = []
  let paragraphCount = 0
  let lastWasEmpty = false

  for (let i = startIdx; i <= endIdx; i++) {
    const line = lines[i]!
    const trimmed = line.trim()

    if (trimmed === '') {
      // Track blank lines; actual blank-line insertion is controlled by
      // paragraphSpacingLines, so we skip them here.
      lastWasEmpty = true
      continue
    }

    // Insert paragraph spacing before this line (if not the first paragraph)
    if (paragraphCount > 0 && options.paragraphSpacingLines > 0) {
      for (let s = 0; s < options.paragraphSpacingLines; s++) {
        result.push('')
      }
    }

    // Strip existing leading whitespace (ASCII space, tab, full-width space)
    // and re-apply configured indent
    const stripped = trimmed.replace(/^[ \t　]+/, '')
    result.push(indent + stripped)
    paragraphCount++
    lastWasEmpty = false
  }

  const resultContent = result.join('\n')
  const changed = resultContent !== content

  if (changed) {
    if (options.firstLineIndentSpaces > 0) {
      changes.push(`首行缩进 ${options.firstLineIndentSpaces} 空格`)
    }
    if (options.paragraphSpacingLines > 0) {
      changes.push(`段落间距 ${options.paragraphSpacingLines} 空行`)
    }
    if (content.includes('\r')) {
      changes.push('统一换行符')
    }
    changes.push('清理行尾空白')
  }

  return { content: resultContent, changed, paragraphCount, changes }
}
