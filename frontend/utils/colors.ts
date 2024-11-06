export const generateColors = (items: string[]): Record<string, string> => {
  const colors = [
    '#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
    '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
    '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9'
  ]

  return items.reduce((acc, item, index) => {
    acc[item] = colors[index % colors.length]
    return acc
  }, {} as Record<string, string>)
} 