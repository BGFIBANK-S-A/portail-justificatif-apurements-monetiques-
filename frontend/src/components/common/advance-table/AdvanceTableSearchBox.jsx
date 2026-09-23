import { useState } from 'react'
import { Button, FormControl, InputGroup } from 'react-bootstrap'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useAdvanceTableContext } from '../../../providers/AdvanceTableProvider'

export default function AdvanceTableSearchBox({ placeholder = 'Rechercher...', className }) {
  const { globalFilter, setGlobalFilter } = useAdvanceTableContext()
  const [value, setValue] = useState(globalFilter)

  function onChange(v) {
    setGlobalFilter(v || undefined)
  }

  return (
    <InputGroup className={['position-relative', className].filter(Boolean).join(' ')}>
      <FormControl
        value={value || ''}
        onChange={(e) => { setValue(e.target.value); onChange(e.target.value) }}
        size="sm"
        id="search"
        placeholder={placeholder}
        type="search"
        className="shadow-none"
      />
      <Button size="sm" variant="outline-secondary" className="border-300 hover-border-secondary">
        <FontAwesomeIcon icon="search" className="fs-10" />
      </Button>
    </InputGroup>
  )
}
