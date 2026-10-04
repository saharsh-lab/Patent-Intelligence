// Small inline icon set (stroke icons, 24-unit grid). Decorative: aria-hidden.
import type { SVGProps } from "react";

function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden {...props}>
      {children}
    </svg>
  );
}

export const icons = {
  home: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" /></Icon>,
  chat: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z" /></Icon>,
  plus: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M12 5v14M5 12h14" /></Icon>,
  file: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></Icon>,
  bulb: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z" /></Icon>,
  search: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Icon>,
  columns: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M12 4v16" /></Icon>,
  bell: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0" /></Icon>,
  chart: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></Icon>,
  flask: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3" /></Icon>,
  gear: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></Icon>,
  paperclip: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="m21 11-8.6 8.6a5 5 0 0 1-7-7l8.5-8.6a3.3 3.3 0 0 1 4.7 4.7L10 17.3a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9" /></Icon>,
  globe: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></Icon>,
  send: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Icon>,
  menu: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M4 6h16M4 12h16M4 18h16" /></Icon>,
  x: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M6 6l12 12M18 6 6 18" /></Icon>,
  sun: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></Icon>,
  moon: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></Icon>,
  logout: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></Icon>,
  trash: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" /></Icon>,
  pencil: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z" /></Icon>,
  user: (p: SVGProps<SVGSVGElement>) => <Icon {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></Icon>,
};
