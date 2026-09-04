'use client'
import { useState } from 'react'
import { PageHeader, Tabs, Input, Select, Button, Spinner } from '@/components/ui'
import { useLibrary, type LibraryTab } from './useLibrary'
import CatalogueTable from './CatalogueTable'
import IssueTable from './IssueTable'

const TABS: LibraryTab[] = ['Catalogue & Search', 'Issue / Return', 'Overdues & Notices']

export default function LibraryPage() {
  const [tab, setTab] = useState<LibraryTab>('Catalogue & Search')
  const lib = useLibrary(tab)

  return (
    <div>
      <PageHeader
        title="Library"
        subtitle="Book catalogue, issue / return, overdues & notices."
        actions={<Button variant="primary">+ Add Book</Button>}
      />

      {lib.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{lib.books.length}</b><span>Titles</span></div>
            <div className="stat-tile"><b>{lib.totalCopies}</b><span>Total Copies</span></div>
            <div className="stat-tile"><b>{lib.issuedCount}</b><span>Borrowed</span></div>
            <div className="stat-tile"><b>{lib.overdueIssues.length}</b><span>Overdue</span></div>
          </div>

          <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as LibraryTab)} />

          {(tab === 'Catalogue & Search' || tab === 'Issue / Return') && (
            <div className="toolbar">
              <div className="toolbar-search">
                <Input placeholder="Search title, author, ISBN, student…" value={lib.query} onChange={(e) => lib.setQuery(e.target.value)} />
              </div>
              {tab === 'Catalogue & Search' && (
                <Select value={lib.category} onChange={(e) => lib.setCategory(e.target.value)}>
                  {lib.categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </Select>
              )}
            </div>
          )}

          {tab === 'Catalogue & Search' && <CatalogueTable rows={lib.filteredBooks} />}
          {tab === 'Issue / Return' && <IssueTable rows={lib.filteredIssues} />}
          {tab === 'Overdues & Notices' && <IssueTable rows={lib.overdueIssues} />}
        </>
      )}
    </div>
  )
}