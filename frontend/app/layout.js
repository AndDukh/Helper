export const metadata = {
  title: "Helper Mini App",
  description: "Meeting capture and AI execution assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "sans-serif", margin: 0, padding: 24 }}>{children}</body>
    </html>
  );
}
