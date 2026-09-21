// Server-side only. Do not import from client components.
export const env = {
  apiUrl: process.env.API_URL ?? 'http://localhost:8000',
}
