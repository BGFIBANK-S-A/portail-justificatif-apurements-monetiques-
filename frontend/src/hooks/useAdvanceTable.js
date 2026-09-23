import {
  useReactTable, getCoreRowModel, getFilteredRowModel, getPaginationRowModel, getSortedRowModel,
} from '@tanstack/react-table'

export default function useAdvanceTable({ columns, data, sortable, pagination, initialState, perPage = 10 }) {
  const state = {
    pagination: { pageSize: pagination ? perPage : data.length },
    ...initialState,
  }
  const table = useReactTable({
    data,
    columns,
    enableSorting: sortable,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: state,
    autoResetPageIndex: false,
  })

  return { ...table, globalFilter: table.getState().globalFilter }
}
