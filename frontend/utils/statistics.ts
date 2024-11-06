export const mean = (values: number[]): number => {
  const sum = values.reduce((acc, val) => acc + val, 0)
  return sum / values.length
}

export const std = (values: number[]): number => {
  const avg = mean(values)
  const squareDiffs = values.map(value => Math.pow(value - avg, 2))
  const avgSquareDiff = mean(squareDiffs)
  return Math.sqrt(avgSquareDiff)
} 