import { COLUMNS, groupByStatus, urgencyLabel, formatPercent, departmentLabel } from '@/lib/board'
import { tickets } from '@/lib/fixtures'

describe('board helpers', () => {
  it('defines the four status columns in order', () => {
    expect(COLUMNS.map((c) => c.status)).toEqual(['new', 'triaged', 'in_progress', 'done'])
    expect(COLUMNS.map((c) => c.label)).toEqual(['New', 'Triaged', 'In progress', 'Done'])
  })

  it('groups tickets by status with every column present', () => {
    const grouped = groupByStatus(tickets)
    expect(grouped.new.map((t) => t.id)).toEqual([1, 2])
    expect(grouped.triaged.map((t) => t.id)).toEqual([3])
    expect(grouped.in_progress.map((t) => t.id)).toEqual([4])
    expect(grouped.done.map((t) => t.id)).toEqual([5])
    expect(groupByStatus([]).done).toEqual([])
  })

  it('labels urgency levels and departments', () => {
    expect(urgencyLabel(1)).toBe('Low')
    expect(urgencyLabel(3)).toBe('Medium')
    expect(urgencyLabel(5)).toBe('Critical')
    expect(departmentLabel('technical')).toBe('Technical')
  })

  it('formats probabilities as percentages', () => {
    expect(formatPercent(0.915)).toBe('92%')
    expect(formatPercent(0)).toBe('0%')
  })
})
