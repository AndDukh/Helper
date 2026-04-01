import Script from "next/script";
import { Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata = {
  title: "Helper Mini App",
  description: "Meeting capture and AI execution assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" className={inter.variable}>
      <body>
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        {children}
      </body>
    </html>
  );
}
