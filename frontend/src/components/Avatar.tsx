// Customer initials on a soft colour that is always the same for the same name.
const TONES=['coral','amber','green','indigo','violet','teal'] as const;

export function initials(name:string) {
  const words=name.replace(/[^\p{L}\p{N}\s]/gu,' ').split(/\s+/).filter(Boolean);
  if(!words.length)return '?';
  const letters=words.length===1?Array.from(words[0]).slice(0,2):[Array.from(words[0])[0],Array.from(words[1])[0]];
  return letters.join('').toUpperCase();
}

export function avatarTone(name:string) {
  let hash=0;
  for(const char of name)hash=(hash*31+(char.codePointAt(0)??0))>>>0;
  return TONES[hash%TONES.length];
}

/** Decorative: the customer's name is always written next to it, so it is hidden from assistive technology. */
export function Avatar({name,size='md'}:{name:string;size?:'sm'|'md'|'lg'}) {
  return <span className={`avatar avatar-${size} avatar-${avatarTone(name)}`} aria-hidden="true">{initials(name)}</span>;
}
