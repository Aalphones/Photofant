export function groupColor(groupName: string): string {
  let hash = 0;
  for (let index = 0; index < groupName.length; index++) {
    hash = (hash << 5) - hash + groupName.charCodeAt(index);
    hash |= 0;
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 55%, 55%)`;
}
