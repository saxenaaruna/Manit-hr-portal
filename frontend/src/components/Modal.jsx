import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";

export default function Modal({ open, onClose, title, children, wide, testid }) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className={`max-h-[90vh] overflow-y-auto ${wide ? "sm:max-w-4xl" : "sm:max-w-lg"}`} data-testid={testid}>
        <DialogHeader><DialogTitle className="font-serif-d text-xl text-[#0B2545]">{title}</DialogTitle></DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}

export const Field = ({ label, children }) => (
  <label className="block"><span className="lbl">{label}</span>{children}</label>
);
