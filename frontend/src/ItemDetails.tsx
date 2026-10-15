import { useState, type ComponentProps } from 'react';
export default function ItemDetails({
  initiallyOpen = false,
  ...props
}: ComponentProps<'details'> & { initiallyOpen?: boolean }) {
  const [open, setOpen] = useState(initiallyOpen);
  return <details {...props} open={open} onToggle={(e) => setOpen(e.currentTarget.open)} />;
}
