import type { ReactNode } from "react";

export const metadata = {
  title: "CAZ-Route & Fleet Sync (Bristol)",
  description: "Bristol Clean Air Zone routing and fleet compliance management prototype",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-GB">
      <body
        style={{
          margin: 0,
          fontFamily: "Arial, Helvetica, sans-serif",
          background: "#edf3f1",
          color: "#12231c",
          WebkitFontSmoothing: "antialiased",
          textRendering: "optimizeLegibility",
        }}
      >
        {children}
      </body>
    </html>
  );
}
