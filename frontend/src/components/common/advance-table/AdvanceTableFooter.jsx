import { useState } from 'react'
import { Button, Form } from 'react-bootstrap'
import Flex from '../Flex'
import { useAdvanceTableContext } from '../../../providers/AdvanceTableProvider'

export default function AdvanceTableFooter({
  navButtons, className, rowInfo, rowsPerPageSelection, rowsPerPageOptions = [5, 10, 15],
}) {
  const {
    setPageSize, previousPage, nextPage, getCanNextPage, getCanPreviousPage,
    getState, getPrePaginationRowModel, getPaginationRowModel,
  } = useAdvanceTableContext()

  const { pagination: { pageSize, pageIndex } } = getState()

  return (
    <Flex className={[className, 'align-items-center justify-content-between'].filter(Boolean).join(' ')}>
      <Flex alignItems="center" className="fs-10">
        {rowInfo && (
          <p className="mb-0">
            <span className="d-none d-sm-inline-block me-2">
              {pageSize * pageIndex + 1} a {pageSize * pageIndex + getPaginationRowModel().rows.length} sur {getPrePaginationRowModel().rows.length}
            </span>
          </p>
        )}
        {rowsPerPageSelection && (
          <>
            <p className="mb-0 mx-2">Lignes par page :</p>
            <Form.Select size="sm" className="w-auto" onChange={(e) => setPageSize(Number(e.target.value))} defaultValue={pageSize}>
              {rowsPerPageOptions.map((value) => <option value={value} key={value}>{value}</option>)}
            </Form.Select>
          </>
        )}
      </Flex>
      {navButtons && (
        <Flex>
          <Button
            size="sm"
            variant={getCanPreviousPage() ? 'primary' : 'tertiary'}
            onClick={() => previousPage()}
            className={getCanPreviousPage() ? '' : 'disabled'}
          >
            Precedent
          </Button>
          <Button
            size="sm"
            variant={getCanNextPage() ? 'primary' : 'tertiary'}
            className={`px-4 ms-2 ${getCanNextPage() ? '' : 'disabled'}`}
            onClick={() => nextPage()}
          >
            Suivant
          </Button>
        </Flex>
      )}
    </Flex>
  )
}
