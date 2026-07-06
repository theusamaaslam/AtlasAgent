import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { setRuntimeI18nLocale, translateNow } from './runtime'

describe('desktop i18n runtime translator', () => {
  beforeEach(() => {
    setRuntimeI18nLocale('en')
  })

  afterEach(() => {
    setRuntimeI18nLocale('en')
  })

  it('translates string paths in English', () => {
    expect(translateNow('boot.ready')).toBe('Atlas Desktop is ready')
    expect(translateNow('notifications.voice.noSpeechDetected')).toBe('No speech detected')
    expect(translateNow('composer.lookupNoMatches')).toBe('No matches.')
    expect(translateNow('assistant.tool.statusRecovered')).toBe('Recovered')
  })

  it('passes arguments to function translations', () => {
    expect(translateNow('notifications.updateReadyMessage', 2)).toBe('2 new changes available.')
  })

  it('returns the key when English cannot resolve a path', () => {
    expect(translateNow('missing.path')).toBe('missing.path')
  })
})
