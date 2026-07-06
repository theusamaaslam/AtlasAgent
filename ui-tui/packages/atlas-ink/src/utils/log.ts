export function logError(error: unknown): void {
  if (!process.env.ATLAS_INK_DEBUG_ERRORS) {
    return
  }

  console.error(error)
}
