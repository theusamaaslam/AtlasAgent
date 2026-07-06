import { useQuery } from '@tanstack/react-query'

import { getAtlasConfigRecord } from '@/atlas'
import { queryClient, writeCache } from '@/lib/query-client'
import type { AtlasConfigRecord } from '@/types/atlas'

// One shared cache for the whole profile config record (`GET /api/config`).
// Every settings surface (MCP, model, config) reads and writes through this key
// so a save in one shows in the others, and revisiting a tab paints the cache
// instead of blanking on a fresh fetch.
//
// Distinct from session/hooks/use-atlas-config.ts, which is side-effecting —
// it pushes personality/cwd/voice/… into the session stores for live chat.
export const ATLAS_CONFIG_KEY = ['atlas-config-record'] as const

// staleTime 0 → serve cache instantly, background-revalidate on every mount.
export const useAtlasConfigRecord = () =>
  useQuery({ queryKey: ATLAS_CONFIG_KEY, queryFn: getAtlasConfigRecord, staleTime: 0 })

export const setAtlasConfigCache = writeCache<AtlasConfigRecord>(ATLAS_CONFIG_KEY)

export const invalidateAtlasConfig = () => queryClient.invalidateQueries({ queryKey: ATLAS_CONFIG_KEY })
