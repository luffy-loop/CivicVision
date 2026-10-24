export type BoxDetection = { label: string; confidence: number; box: number[] }

export async function makeAnnotatedImage(source: string, detections: BoxDetection[]): Promise<string> {
  const image = new Image()
  image.src = source
  await image.decode()

  const scale = Math.min(1, 2048 / Math.max(image.naturalWidth, image.naturalHeight))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(image.naturalWidth * scale)
  canvas.height = Math.round(image.naturalHeight * scale)
  const context = canvas.getContext('2d')
  if (!context) throw new Error('This browser cannot prepare an annotated image.')
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  context.lineWidth = Math.max(2, Math.round(Math.min(canvas.width, canvas.height) / 260))
  context.font = `600 ${Math.max(13, Math.round(canvas.width / 55))}px sans-serif`

  detections.forEach(({ label, confidence, box }) => {
    if (box.length !== 4) return
    const [x1, y1, x2, y2] = box.map(value => value * scale)
    context.strokeStyle = '#6F4E37'
    context.fillStyle = '#6F4E37'
    context.strokeRect(x1, y1, x2 - x1, y2 - y1)
    const caption = `${label} · ${(confidence * 100).toFixed(1)}%`
    const textWidth = context.measureText(caption).width
    const captionY = Math.max(0, y1 - 25)
    context.fillRect(x1, captionY, textWidth + 14, 24)
    context.fillStyle = '#fff'
    context.fillText(caption, x1 + 7, captionY + 17)
  })

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(value => value ? resolve(value) : reject(new Error('Could not encode the annotated image.')), 'image/jpeg', 0.9)
  })
  return URL.createObjectURL(blob)
}
