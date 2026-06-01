/**
 * Helpers for parsing/formatting multi-faction strings.
 *
 * The backend stores multiple factions in a single `faction: string | null`
 * field, joined by the Chinese enumeration comma `、`.
 * The frontend also accepts common delimiters when parsing user input.
 */

/** Delimiters accepted when parsing a faction string into tags. */
const FACTION_SPLIT_RE = /[、,，;；/]/

/** Canonical delimiter used when joining tags for storage. */
export const FACTION_JOIN_SEPARATOR = '、'

/** Delimiters that should trigger a new tag when typed in the input. */
export const FACTION_INPUT_DELIMITERS = ['Enter', ',', '，', '、']

/** Parse a faction string into an array of trimmed, non-empty tag strings. */
export function parseFactionTags(value: string | null | undefined): string[] {
  if (!value) return []
  return value
    .split(FACTION_SPLIT_RE)
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0)
}

/** Join an array of tags into a single faction string, or null if empty. */
export function formatFactionTags(tags: string[]): string | null {
  const cleaned = tags.map((t) => t.trim()).filter((t) => t.length > 0)
  return cleaned.length > 0 ? cleaned.join(FACTION_JOIN_SEPARATOR) : null
}

/** Format tags for compact display in a character card (max 2 + "+N"). */
export function formatFactionDisplay(
  tags: string[],
  maxVisible = 2,
): { visible: string[]; overflow: number } {
  const visible = tags.slice(0, maxVisible)
  const overflow = Math.max(0, tags.length - maxVisible)
  return { visible, overflow }
}
