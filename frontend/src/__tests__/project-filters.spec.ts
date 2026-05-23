import { describe, it, expect } from 'vitest'

import type { Project } from '@/entities/project/types'

import {
  collectProjectTags,
  countActiveFilters,
  filterProjects,
  sortProjects,
  type ProjectFilterState,
} from '../features/projects/projectFilters'

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: '1',
    title: '测试项目',
    author: '测试作者',
    genre: '玄幻',
    summary: '这是一段测试简介',
    tags: ['玄幻', '长篇'],
    cover_image_path: null,
    status: 'writing',
    target_word_count: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    deleted_at: null,
    version: 1,
    ...overrides,
  }
}

const defaultFilters: ProjectFilterState = { keyword: '', status: '', tag: '' }

describe('filterProjects', () => {
  const projects = [
    makeProject({ id: '1', title: '星辰大海', author: '张三', tags: ['科幻', '长篇'], status: 'writing' }),
    makeProject({ id: '2', title: '都市传说', author: '李四', tags: ['都市', '短篇'], status: 'completed' }),
    makeProject({ id: '3', title: '仙侠风云', author: '张三', tags: ['仙侠', '长篇'], status: 'planning' }),
  ]

  it('returns all projects with empty filters', () => {
    expect(filterProjects(projects, defaultFilters)).toHaveLength(3)
  })

  it('filters by keyword in title', () => {
    expect(filterProjects(projects, { ...defaultFilters, keyword: '星辰' })).toHaveLength(1)
  })

  it('filters by keyword in author', () => {
    expect(filterProjects(projects, { ...defaultFilters, keyword: '张三' })).toHaveLength(2)
  })

  it('filters by keyword case-insensitively', () => {
    expect(filterProjects(projects, { ...defaultFilters, keyword: '都市' })).toHaveLength(1)
  })

  it('filters by status', () => {
    expect(filterProjects(projects, { ...defaultFilters, status: 'writing' })).toHaveLength(1)
  })

  it('filters by tag', () => {
    expect(filterProjects(projects, { ...defaultFilters, tag: '长篇' })).toHaveLength(2)
  })

  it('combines multiple filters', () => {
    const result = filterProjects(projects, { keyword: '张三', status: 'writing', tag: '' })
    expect(result).toHaveLength(1)
    expect(result[0]!.title).toBe('星辰大海')
  })

  it('returns empty when no match', () => {
    expect(filterProjects(projects, { ...defaultFilters, keyword: '不存在' })).toHaveLength(0)
  })
})

describe('sortProjects', () => {
  const projects = [
    makeProject({ id: '1', title: 'B项目', author: '李四', updated_at: '2026-01-01T00:00:00Z', created_at: '2026-03-01T00:00:00Z' }),
    makeProject({ id: '2', title: 'A项目', author: '张三', updated_at: '2026-02-01T00:00:00Z', created_at: '2026-01-01T00:00:00Z' }),
    makeProject({ id: '3', title: 'C项目', author: '王五', updated_at: '2026-03-01T00:00:00Z', created_at: '2026-02-01T00:00:00Z' }),
  ]

  it('sorts by updated_at descending', () => {
    const sorted = sortProjects(projects, 'updated_at')
    expect(sorted[0]!.id).toBe('3')
    expect(sorted[2]!.id).toBe('1')
  })

  it('sorts by created_at descending', () => {
    const sorted = sortProjects(projects, 'created_at')
    expect(sorted[0]!.id).toBe('1')
    expect(sorted[2]!.id).toBe('2')
  })

  it('sorts by title ascending', () => {
    const sorted = sortProjects(projects, 'title')
    expect(sorted[0]!.id).toBe('2')
    expect(sorted[2]!.id).toBe('3')
  })

  it('sorts by author ascending', () => {
    const sorted = sortProjects(projects, 'author')
    expect(sorted[0]!.author).toBe('李四')
  })

  it('does not mutate original array', () => {
    const original = [...projects]
    sortProjects(projects, 'title')
    expect(projects[0]!.id).toBe(original[0]!.id)
  })
})

describe('collectProjectTags', () => {
  it('merges project tags with builtin tags', () => {
    const projects = [makeProject({ tags: ['自定义'] })]
    const result = collectProjectTags(projects, ['内置'])
    expect(result).toContain('内置')
    expect(result).toContain('自定义')
  })

  it('deduplicates tags', () => {
    const projects = [makeProject({ tags: ['玄幻'] })]
    const result = collectProjectTags(projects, ['玄幻'])
    expect(result.filter((t) => t === '玄幻')).toHaveLength(1)
  })
})

describe('countActiveFilters', () => {
  it('returns 0 for empty filters', () => {
    expect(countActiveFilters(defaultFilters)).toBe(0)
  })

  it('counts status and tag filters', () => {
    expect(countActiveFilters({ keyword: 'test', status: 'writing', tag: '玄幻' })).toBe(2)
  })

  it('does not count keyword as a filter', () => {
    expect(countActiveFilters({ keyword: 'test', status: '', tag: '' })).toBe(0)
  })
})
