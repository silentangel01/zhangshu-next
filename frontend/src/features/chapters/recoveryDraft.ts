export interface RecoveryDraft {
  id?: string
  chapter_id: string
  content: string
  saved_content_snapshot: string
  updated_at: string
  word_count: number
}

export function calculateContentWordCount(content: string): number {
  return Array.from(content).filter((character) => !/\s/.test(character)).length
}

export function getRecoveryDraft(chapterId: string): RecoveryDraft | null {
  try {
    const rawDraft = window.localStorage.getItem(getRecoveryDraftKey(chapterId))
    return rawDraft ? (JSON.parse(rawDraft) as RecoveryDraft) : null
  } catch {
    return null
  }
}

export function saveRecoveryDraft(draft: RecoveryDraft): void {
  window.localStorage.setItem(getRecoveryDraftKey(draft.chapter_id), JSON.stringify(draft))
}

export function clearRecoveryDraft(chapterId: string): void {
  window.localStorage.removeItem(getRecoveryDraftKey(chapterId))
}

function getRecoveryDraftKey(chapterId: string): string {
  return `zhangshu:recovery-draft:${chapterId}`
}
