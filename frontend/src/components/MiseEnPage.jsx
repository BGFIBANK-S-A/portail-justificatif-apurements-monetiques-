import { useState } from 'react'
import NavbarVertical from './navbar/NavbarVertical'
import NavbarTop from './navbar/NavbarTop'
import Footer from './footer/Footer'

export default function MiseEnPage({ children, titre }) {
  const [sidebarOuverte, setSidebarOuverte] = useState(false)
  return (
    <div className="container-fluid">
      <NavbarVertical ouvert={sidebarOuverte} onToggle={setSidebarOuverte} />
      <div className="content">
        <NavbarTop titre={titre} onToggleSidebar={() => setSidebarOuverte((o) => !o)} />
        <div className="pt-3">{children}</div>
        <Footer />
      </div>
    </div>
  )
}
