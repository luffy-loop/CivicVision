export const MAX_CITIZEN_PHOTO_BYTES = 8 * 1024 * 1024
const SUPPORTED_PHOTO_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

export function validateCitizenPhoto(file: Pick<File, 'type' | 'size'>): string | null {
  if (!SUPPORTED_PHOTO_TYPES.has(file.type)) return 'Choose a JPG, PNG or WebP photo.'
  if (file.size > MAX_CITIZEN_PHOTO_BYTES) return 'Photo must be 8 MB or smaller. Choose a smaller image.'
  return null
}

export function cameraFailureMessage(name: string): string {
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Camera permission was denied. Allow camera access in your browser settings, or choose a photo instead.'
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') return 'No camera is available on this device. Choose a photo instead.'
  return 'The camera could not start. Check browser permissions and try again, or choose a photo.'
}

export function locationFailureMessage(code: number): string {
  if (code === 1) return 'Location permission was denied. You may enter coordinates manually or submit without a verified location.'
  return 'Location could not be determined. Retry, enter coordinates manually, or submit without a verified location.'
}
