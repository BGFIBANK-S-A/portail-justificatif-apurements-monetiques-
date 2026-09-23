import { createContext, useContext } from 'react'

export const AdvanceTableContext = createContext({})

export default function AdvanceTableProvider({ children, ...rest }) {
  return (
    <AdvanceTableContext.Provider value={{ ...rest }}>
      {children}
    </AdvanceTableContext.Provider>
  )
}

export const useAdvanceTableContext = () => useContext(AdvanceTableContext)
