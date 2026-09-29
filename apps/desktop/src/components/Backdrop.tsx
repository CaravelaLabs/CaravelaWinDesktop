import { useTheme } from '@/themes'
import { useStore } from '@nanostores/react'

import { $backdrop } from '@/store/backdrop'

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

export function Backdrop() {
  const on = useStore($backdrop)
  const { theme } = useTheme()
  const branding = theme.branding
  const backdropUrl = branding?.backdropUrl
  const motif = branding?.backdropMode === 'motif' && backdropUrl

  if (!on && !motif) {
    return null
  }

  if (motif) {
    return (
      <div aria-hidden className="pointer-events-none absolute inset-0 z-2" role="img" aria-label="Caravela atmospheric backdrop">
        <img alt="" className="h-full w-full object-cover" fetchPriority="low" src={assetPath(backdropUrl)} />
      </div>
    )
  }

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-2 opacity-[0.025] mix-blend-difference">
      <img
        alt=""
        className="h-[160dvh] w-auto min-w-dvw object-cover object-left-top [filter:invert(var(--backdrop-invert-mul,1))]"
        fetchPriority="low"
        src={assetPath(backdropUrl ?? 'ds-assets/filler-bg0.jpg')}
      />
    </div>
  )
}
