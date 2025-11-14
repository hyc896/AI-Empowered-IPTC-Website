export interface MessageSourcePlugin {
  name: string
  ConfigForm: any
  validateConfig: (config: any) => { valid: boolean; error?: string }
}

export function getPlugin(adapterName: string): MessageSourcePlugin | null {
  return null
}
