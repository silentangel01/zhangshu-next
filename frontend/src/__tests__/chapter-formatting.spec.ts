import { describe, expect, it } from 'vitest'

import { formatChapterContent } from '../features/chapters/chapterFormatting'

describe('formatChapterContent', () => {
  // --- Line ending normalisation ---

  it('normalises CRLF to LF', () => {
    const result = formatChapterContent('第一段。\r\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。\n第二段。')
  })

  it('normalises CR to LF', () => {
    const result = formatChapterContent('第一段。\r第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。\n第二段。')
  })

  // --- Trailing whitespace removal ---

  it('removes trailing whitespace from each line', () => {
    const result = formatChapterContent('第一段。   \n第二段。\t\t', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。\n第二段。')
  })

  // --- First-line indent ---

  it('adds 2-space indent to non-empty paragraphs', () => {
    const result = formatChapterContent('第一段。\n第二段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('  第一段。\n  第二段。')
  })

  it('adds 4-space indent to non-empty paragraphs', () => {
    const result = formatChapterContent('第一段。', {
      firstLineIndentSpaces: 4,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('    第一段。')
  })

  it('does not add indent when set to 0', () => {
    const result = formatChapterContent('第一段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。')
  })

  // --- Existing indent handling ---

  it('strips existing ASCII spaces before re-applying indent', () => {
    const result = formatChapterContent('  第一段。\n    第二段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('  第一段。\n  第二段。')
  })

  it('strips existing tabs before re-applying indent', () => {
    const result = formatChapterContent('\t第一段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('  第一段。')
  })

  it('strips full-width spaces before re-applying indent', () => {
    const result = formatChapterContent('　　第一段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('  第一段。')
  })

  it('does not double-indent already-indented content', () => {
    const result = formatChapterContent('  第一段。\n  第二段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('  第一段。\n  第二段。')
    expect(result.changed).toBe(false)
  })

  // --- Empty line handling ---

  it('does not add indent to empty lines', () => {
    const result = formatChapterContent('第一段。\n\n第二段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 1,
    })
    const lines = result.content.split('\n')
    for (const line of lines) {
      if (line.trim() === '') {
        expect(line).toBe('')
      }
    }
  })

  // --- Paragraph spacing ---

  it('inserts 1 blank line between paragraphs when spacing is 1', () => {
    const result = formatChapterContent('第一段。\n第二段。\n第三段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('第一段。\n\n第二段。\n\n第三段。')
  })

  it('inserts 2 blank lines between paragraphs when spacing is 2', () => {
    const result = formatChapterContent('第一段。\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 2,
    })
    expect(result.content).toBe('第一段。\n\n\n第二段。')
  })

  it('removes blank lines between paragraphs when spacing is 0', () => {
    const result = formatChapterContent('第一段。\n\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。\n第二段。')
  })

  // --- Collapsing excessive blank lines ---

  it('collapses 3+ blank lines to configured spacing of 1', () => {
    const result = formatChapterContent('第一段。\n\n\n\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('第一段。\n\n第二段。')
  })

  it('collapses 5 blank lines to configured spacing of 2', () => {
    const result = formatChapterContent('第一段。\n\n\n\n\n\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 2,
    })
    expect(result.content).toBe('第一段。\n\n\n第二段。')
  })

  it('collapses blank lines to zero when spacing is 0', () => {
    const result = formatChapterContent('第一段。\n\n\n\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。\n第二段。')
  })

  // --- Does not merge consecutive non-empty lines ---

  it('does not merge consecutive non-empty lines', () => {
    const result = formatChapterContent('你好。\n他说。\n她走了。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('你好。\n他说。\n她走了。')
    expect(result.changed).toBe(false)
  })

  it('preserves consecutive non-empty lines with spacing', () => {
    const result = formatChapterContent('你好。\n他说。\n她走了。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('你好。\n\n他说。\n\n她走了。')
  })

  // --- Empty content ---

  it('handles empty string without error', () => {
    const result = formatChapterContent('', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('')
    expect(result.changed).toBe(false)
    expect(result.paragraphCount).toBe(0)
  })

  it('handles whitespace-only content', () => {
    const result = formatChapterContent('   \n  \n   ', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('')
    expect(result.paragraphCount).toBe(0)
  })

  // --- Trailing newline handling ---

  it('ensures at most one trailing newline', () => {
    const result = formatChapterContent('第一段。\n\n\n', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。')
  })

  it('trims leading blank lines', () => {
    const result = formatChapterContent('\n\n\n第一段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.content).toBe('第一段。')
  })

  // --- changed flag ---

  it('reports changed=false when content is already formatted', () => {
    const result = formatChapterContent('第一段。\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.changed).toBe(false)
    expect(result.changes).toEqual([])
  })

  it('reports changed=true when indent is applied', () => {
    const result = formatChapterContent('第一段。\n第二段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 0,
    })
    expect(result.changed).toBe(true)
    expect(result.changes.length).toBeGreaterThan(0)
  })

  it('reports changed=true when spacing is applied', () => {
    const result = formatChapterContent('第一段。\n第二段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 1,
    })
    expect(result.changed).toBe(true)
  })

  // --- paragraphCount ---

  it('counts non-empty paragraphs correctly', () => {
    const result = formatChapterContent('第一段。\n\n第二段。\n\n第三段。', {
      firstLineIndentSpaces: 0,
      paragraphSpacingLines: 0,
    })
    expect(result.paragraphCount).toBe(3)
  })

  // --- Combined operations ---

  it('applies indent and spacing together', () => {
    const result = formatChapterContent('第一段。\n  第二段。\n\n\n\n第三段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('  第一段。\n\n  第二段。\n\n  第三段。')
  })

  it('handles CRLF + trailing whitespace + indent + spacing all at once', () => {
    const result = formatChapterContent('第一段。  \r\n  第二段。\t\r\n\r\n\r\n第三段。', {
      firstLineIndentSpaces: 2,
      paragraphSpacingLines: 1,
    })
    expect(result.content).toBe('  第一段。\n\n  第二段。\n\n  第三段。')
    expect(result.changed).toBe(true)
  })
})
