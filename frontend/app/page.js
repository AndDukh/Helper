async function callApi(path, options = {}) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    return { error: `Request failed: ${response.status}` };
  }
  return response.json();
}

export default async function HomePage() {
  const health = await callApi("/health");

  return (
    <main>
      <h1>Helper Mini App</h1>
      <p>Bootstrap UI for meeting workflow.</p>
      <pre>{JSON.stringify(health, null, 2)}</pre>
      <p>Next steps: add Telegram auth and meeting controls.</p>
    </main>
  );
}
