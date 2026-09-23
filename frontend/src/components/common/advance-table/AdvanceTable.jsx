import { Table } from 'react-bootstrap'
import { flexRender } from '@tanstack/react-table'
import { useAdvanceTableContext } from '../../../providers/AdvanceTableProvider'

export default function AdvanceTable({ headerClassName, bodyClassName, rowClassName, tableProps }) {
  const table = useAdvanceTableContext()
  const { getRowModel, getFlatHeaders } = table

  return (
    <div className="table-responsive scrollbar">
      <Table {...tableProps}>
        <thead className={headerClassName}>
          <tr>
            {getFlatHeaders().map((header) => (
              <th
                key={header.id}
                {...header.column.columnDef.meta?.headerProps}
                className={[
                  'fs-10',
                  header.column.columnDef.meta?.headerProps?.className,
                  header.column.getCanSort() ? 'sort' : '',
                  header.column.getIsSorted() === 'desc' ? 'desc' : '',
                  header.column.getIsSorted() === 'asc' ? 'asc' : '',
                ].filter(Boolean).join(' ')}
                onClick={header.column.getToggleSortingHandler()}
              >
                {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={bodyClassName}>
          {getRowModel().rows.map((row) => (
            <tr key={row.id} className={rowClassName}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} {...cell.column.columnDef.meta?.cellProps}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  )
}
