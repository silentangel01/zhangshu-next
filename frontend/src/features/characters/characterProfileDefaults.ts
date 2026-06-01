import type {
  Character,
  CharacterProfileDimension,
  CharacterProfileSection,
} from '@/entities/character/types'

let _counter = 0

/** Generate a stable unique ID for profile items. */
export function createProfileId(prefix: string): string {
  _counter += 1
  return `${prefix}_${Date.now().toString(36)}_${_counter}`
}

/** Legacy fixed field definitions mapped to default section titles. */
const LEGACY_FIELD_MAP: Array<{ field: keyof Character; title: string }> = [
  { field: 'appearance', title: '外貌' },
  { field: 'personality', title: '性格' },
  { field: 'background', title: '背景' },
  { field: 'ability', title: '能力' },
  { field: 'motivation', title: '动机' },
  { field: 'secret', title: '秘密' },
  { field: 'arc', title: '成长线' },
  { field: 'notes', title: '备注' },
]

/** Create default profile sections from legacy character fields. */
export function legacyFieldsToSections(character: Character): CharacterProfileSection[] {
  return LEGACY_FIELD_MAP.map((entry, index) => ({
    id: createProfileId('sec'),
    title: entry.title,
    content: (character[entry.field] as string) || '',
    order: index,
    collapsed: false,
  }))
}

/** Map profile sections back to legacy fields (by title match). */
export function sectionsToLegacyFields(
  sections: CharacterProfileSection[],
): Partial<Pick<Character, 'appearance' | 'personality' | 'background' | 'ability' | 'motivation' | 'secret' | 'arc' | 'notes'>> {
  const result: Record<string, string> = {}
  const titleToField = new Map(LEGACY_FIELD_MAP.map(e => [e.title, e.field as string]))

  for (const section of sections) {
    const field = titleToField.get(section.title)
    if (field) {
      result[field] = section.content
    }
  }

  return result as Partial<Pick<Character, 'appearance' | 'personality' | 'background' | 'ability' | 'motivation' | 'secret' | 'arc' | 'notes'>>
}

/** Create a new empty profile section. */
export function createEmptySection(order: number): CharacterProfileSection {
  return {
    id: createProfileId('sec'),
    title: '未命名资料',
    content: '',
    order,
    collapsed: false,
  }
}

/** Default dimensions for the radar chart. */
const DEFAULT_DIMENSION_NAMES = ['行动力', '智谋', '情绪稳定', '社交影响', '道德弹性', '剧情驱动力']

/** Create default profile dimensions. */
export function createDefaultProfileDimensions(): CharacterProfileDimension[] {
  return DEFAULT_DIMENSION_NAMES.map((name, index) => ({
    id: createProfileId('dim'),
    name,
    value: 50,
    max: 100,
    order: index,
  }))
}

/** Create a new empty dimension. */
export function createEmptyDimension(order: number, max = 100): CharacterProfileDimension {
  return {
    id: createProfileId('dim'),
    name: '新维度',
    value: max / 2,
    max,
    order,
  }
}

// ---------------------------------------------------------------------------
// Dimension scale modes
// ---------------------------------------------------------------------------

export interface DimensionScaleMode {
  key: 'five' | 'ten' | 'hundred'
  label: string
  max: number
  step: number
}

export const DIMENSION_SCALE_MODES: DimensionScaleMode[] = [
  { key: 'five', label: '5 分制', max: 5, step: 0.5 },
  { key: 'ten', label: '10 分制', max: 10, step: 0.5 },
  { key: 'hundred', label: '100 分制', max: 100, step: 1 },
]

/** Detect the current scale mode from an array of dimensions.
 *  Returns the matching mode if all maxes agree; otherwise falls back to 100. */
export function detectScaleMode(dimensions: CharacterProfileDimension[]): DimensionScaleMode {
  if (dimensions.length === 0) return DIMENSION_SCALE_MODES[2]!
  const firstMax = dimensions[0]!.max
  const allSame = dimensions.every((d) => d.max === firstMax)
  if (allSame) {
    const match = DIMENSION_SCALE_MODES.find((m) => m.max === firstMax)
    if (match) return match
  }
  return DIMENSION_SCALE_MODES[2]!
}

/** Snap a value to the nearest step. */
export function snapToStep(value: number, step: number): number {
  if (step <= 0) return Math.round(value)
  const snapped = Math.round(value / step) * step
  return Math.round(snapped * 10) / 10
}

/** Convert dimensions from one scale mode to another, preserving ratio. */
export function convertDimensionsToScale(
  dimensions: CharacterProfileDimension[],
  targetMode: DimensionScaleMode,
): CharacterProfileDimension[] {
  return dimensions.map((dim) => {
    const ratio = dim.max > 0 ? dim.value / dim.max : 0
    const newValue = snapToStep(ratio * targetMode.max, targetMode.step)
    return {
      ...dim,
      value: Math.max(0, Math.min(targetMode.max, newValue)),
      max: targetMode.max,
    }
  })
}
