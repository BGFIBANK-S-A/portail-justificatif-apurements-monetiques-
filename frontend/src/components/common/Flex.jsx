export default function Flex({ justifyContent, alignItems, className, children, ...rest }) {
  const classes = [
    'd-flex',
    justifyContent ? `justify-content-${justifyContent}` : '',
    alignItems ? `align-items-${alignItems}` : '',
    className,
  ].filter(Boolean).join(' ')
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  )
}
