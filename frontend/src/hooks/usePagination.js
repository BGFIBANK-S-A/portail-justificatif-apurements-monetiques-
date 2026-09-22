import { useMemo, useState } from 'react'

export function usePagination(items, parPage = 10) {
  const [page, setPage] = useState(1)
  const totalPages = Math.max(1, Math.ceil(items.length / parPage))
  const pageBornee = Math.min(page, totalPages)

  const itemsPage = useMemo(
    () => items.slice((pageBornee - 1) * parPage, pageBornee * parPage),
    [items, pageBornee, parPage]
  )

  return { page: pageBornee, setPage, totalPages, itemsPage, total: items.length }
}
