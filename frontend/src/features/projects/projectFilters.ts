import type { Project, ProjectStatus } from '@/entities/project/types'

export type ProjectSortKey = 'updated_at' | 'created_at' | 'title' | 'author'

export interface ProjectFilterState {
  keyword: string
  status: ProjectStatus | ''
  tag: string
}

export function filterProjects(projects: Project[], filters: ProjectFilterState): Project[] {
  const keyword = filters.keyword.trim().toLowerCase()
  const status = filters.status
  const tag = filters.tag

  return projects.filter((project) => {
    if (status && project.status !== status) {
      return false
    }

    if (tag && !project.tags.includes(tag)) {
      return false
    }

    if (keyword) {
      const haystack = [
        project.title,
        project.author || '',
        project.summary || '',
        ...project.tags,
      ]
        .join(' ')
        .toLowerCase()

      if (!haystack.includes(keyword)) {
        return false
      }
    }

    return true
  })
}

export function sortProjects(projects: Project[], sortKey: ProjectSortKey): Project[] {
  const sorted = [...projects]

  switch (sortKey) {
    case 'updated_at':
      sorted.sort((a, b) => b.updated_at.localeCompare(a.updated_at))
      break
    case 'created_at':
      sorted.sort((a, b) => b.created_at.localeCompare(a.created_at))
      break
    case 'title':
      sorted.sort((a, b) => a.title.localeCompare(b.title, 'zh-Hans-CN'))
      break
    case 'author':
      sorted.sort((a, b) => {
        const aAuthor = a.author || ''
        const bAuthor = b.author || ''
        return aAuthor.localeCompare(bAuthor, 'zh-Hans-CN') || a.title.localeCompare(b.title, 'zh-Hans-CN')
      })
      break
  }

  return sorted
}

export function collectProjectTags(projects: Project[], builtinTags: string[]): string[] {
  const collected = new Set<string>(builtinTags)
  for (const project of projects) {
    for (const tag of project.tags) {
      collected.add(tag)
    }
  }
  return [...collected]
}

export function countActiveFilters(filters: ProjectFilterState): number {
  let count = 0
  if (filters.status) count++
  if (filters.tag) count++
  return count
}
