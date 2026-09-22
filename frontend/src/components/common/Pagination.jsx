import { Pagination as PaginationBs } from 'react-bootstrap'

export default function Pagination({ page, totalPages, onChange, total }) {
  if (totalPages <= 1) return null

  const pages = Array.from({ length: totalPages }, (_, i) => i + 1)

  return (
    <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 px-3 py-2">
      {typeof total === 'number' && <span className="fs-10 text-body-secondary">{total} resultat(s)</span>}
      <PaginationBs size="sm" className="mb-0 ms-auto">
        <PaginationBs.Prev disabled={page === 1} onClick={() => onChange(page - 1)} />
        {pages.map((p) => (
          <PaginationBs.Item key={p} active={p === page} onClick={() => onChange(p)}>
            {p}
          </PaginationBs.Item>
        ))}
        <PaginationBs.Next disabled={page === totalPages} onClick={() => onChange(page + 1)} />
      </PaginationBs>
    </div>
  )
}
