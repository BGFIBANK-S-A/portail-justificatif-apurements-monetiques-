export default function SubtleBadge({ bg = 'primary', pill, children, className }) {
  const classes = ['badge', `badge-subtle-${bg}`, pill ? 'rounded-pill' : '', className].filter(Boolean).join(' ')
  return <span className={classes}>{children}</span>
}
