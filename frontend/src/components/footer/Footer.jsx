export default function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="footer">
      <div className="row g-0 justify-content-between fs-10 mt-4 mb-3 text-body-secondary">
        <div className="col-12 text-center">
          BGFIBank Gabon © {year} · Plateforme securisee · Donnees chiffrees
        </div>
      </div>
    </footer>
  )
}
