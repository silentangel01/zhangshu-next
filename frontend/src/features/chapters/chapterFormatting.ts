/**
 * Pure functions for chapter content formatting.
 * No DOM access, no API calls, no localStorage.
 *
 * Formatting rules follow web-novel conventions (起点中文网 / 番茄小说):
 *  - First-line indent with 2 half-width spaces (configurable 0/2/4).
 *  - Scene separators (***, ————, ……) are recognised and NOT indented.
 *  - Half-width punctuation adjacent to CJK text is normalised to full-width.
 *  - Excessive blank lines are collapsed to the configured paragraph spacing.
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

// ─── Scene separator detection ─────────────────────────────────────────────

/**
 * Returns true when the trimmed line consists entirely of scene-separator
 * characters (asterisks, dashes, em-dashes, ellipses, dots, diamonds, etc.)
 * and is at least 2 non-whitespace characters long.
 *
 * Examples:  ***  |  * * *  |  ————————  |  - - -  |  ……  |  ✦✦✦
 */
function isSceneSeparator(trimmedLine: string): boolean {
  if (trimmedLine.length < 2) return false
  return /^[\s*·•✦◆※★☆●○—\-–…·.·]+$/.test(trimmedLine)
}

// ─── Punctuation normalisation ─────────────────────────────────────────────

const CJK = '\\u4e00-\\u9fff\\u3400-\\u4dbf'

const PUNCT_MAP: Record<string, string> = {
  '.': '。',
  '!': '！',
  '?': '？',
  ',': '，',
  ':': '：',
  ';': '；',
}

const PUNCT_RE = new RegExp(`(?<=[${CJK}])[.!?,:;](?=[${CJK}])`, 'g')

/**
 * Convert half-width punctuation to full-width when the character on both
 * sides is CJK.  English phrases embedded in Chinese text are left intact.
 *
 *   你好!世界  →  你好！世界   (both neighbours CJK)
 *   Hello,世界  →  Hello,世界   (left neighbour is ASCII — skip)
 */
function normalisePunctuation(text: string): string {
  // Step 1: context-aware conversion (CJK on both sides)
  let result = text.replace(PUNCT_RE, (m) => PUNCT_MAP[m] ?? m)

  // Step 2: sentence-ending punctuation at line end after CJK
  //   e.g.  "你好!" → "你好！"  "她走了." → "她走了。"
  //   Negative lookbehind prevents "..." → "。。。" (ellipsis stays intact)
  const lineEndRe = new RegExp(`(?<=[${CJK}])(?<![.!?,:;])([.!?])(?=$|\\n)`, 'g')
  result = result.replace(lineEndRe, (m) => PUNCT_MAP[m] ?? m)

  return result
}

// ─── Main formatter ────────────────────────────────────────────────────────

/**
 * Format chapter content according to the given rules.
 *
 * Pipeline:
 *  1. Normalise line endings to LF.
 *  2. Strip trailing whitespace from every line.
 *  3. Convert half-width punctuation to full-width (CJK context only).
 *  4. Trim leading / trailing blank lines from the document.
 *  5. For each non-empty line:
 *     - Scene separators → strip leading whitespace, NO indent.
 *     - Regular paragraphs → strip & re-apply configured indent.
 *  6. Insert the configured number of blank lines between paragraphs.
 *  7. Collapse runs of 3+ blank lines to the configured spacing.
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

  // 3. Punctuation normalisation
  const punctNormalised = normalisePunctuation(normalised)
  const didNormalisePunct = punctNormalised !== normalised
  normalised = punctNormalised

  // 4. Split into lines
  const lines = normalised.split('\n')

  // Trim leading blank lines
  let startIdx = 0
  while (startIdx < lines.length && lines[startIdx]!.trim() === '') {
    startIdx++
  }

  // Trim trailing blank lines
  let endIdx = lines.length - 1
  while (endIdx >= startIdx && lines[endIdx]!.trim() === '') {
    endIdx--
  }

  if (startIdx > endIdx) {
    return { content: '', changed: true, paragraphCount: 0, changes: ['清理空白内容'] }
  }

  const indent =
    options.firstLineIndentSpaces > 0
      ? ' '.repeat(options.firstLineIndentSpaces)
      : ''

  const result: string[] = []
  let paragraphCount = 0
  let separatorHandled = false

  for (let i = startIdx; i <= endIdx; i++) {
    const line = lines[i]!
    const trimmed = line.trim()

    if (trimmed === '') {
      continue
    }

    // Insert paragraph spacing before this line (if not the first paragraph)
    if (paragraphCount > 0 && options.paragraphSpacingLines > 0) {
      for (let s = 0; s < options.paragraphSpacingLines; s++) {
        result.push('')
      }
    }

    // Strip existing leading whitespace (ASCII space, tab, full-width space)
    const stripped = trimmed.replace(/^[ \t ]+/, '')

    if (isSceneSeparator(stripped)) {
      // Scene separator → preserve without indent
      result.push(stripped)
      separatorHandled = true
    } else {
      // Regular paragraph → apply configured indent
      result.push(indent + stripped)
    }

    paragraphCount++
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
    if (separatorHandled) {
      changes.push('场景分隔符不缩进')
    }
    if (didNormalisePunct) {
      changes.push('标点符号规范化')
    }
    if (content.includes('\r')) {
      changes.push('统一换行符')
    }
    changes.push('清理行尾空白')
  }

  return { content: resultContent, changed, paragraphCount, changes }
}
