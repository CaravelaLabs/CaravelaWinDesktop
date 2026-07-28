import { useStore } from '@nanostores/react'

import { $backdrop } from '@/store/backdrop'
import { useTheme } from '@/themes/context'

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

export function Backdrop() {
  const on = useStore($backdrop)
  const { theme } = useTheme()
  const branding = theme.branding
  const backdropUrl = branding?.backdropUrl
  // 'motif' = brand illustration (SVG/PNG) rendered as-is, full-cover.
  // 'photo' (default) = photo treatment with the invert/blend filter
  // tuned for the default backdrop. Branded themes that ship a motif opt into
  // the clean path so their identity asset isn't put through the photo filter.
  const motifMode = branding?.backdropMode === 'motif'

  if (!on) {
    return null
  }

  if (motifMode && backdropUrl) {
    return (
      <div aria-hidden className="pointer-events-none absolute inset-0 z-2 overflow-hidden">
        <img
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
          fetchPriority="low"
          src={assetPath(backdropUrl)}
        />
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
