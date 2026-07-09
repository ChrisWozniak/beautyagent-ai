/**
 * @typedef {'tower_28' | 'half_magic'} BrandId
 * Contract uses "tower_28" and "half_magic" (snake_case, locked).
 *
 * @typedef {'tiktok' | 'instagram' | 'email'} Channel
 *
 * @typedef {'completed' | 'error'} GenerationStatus
 *
 * @typedef {'PASSED' | 'FAILED'} ComplianceStatus
 *
 * @typedef {'deterministic' | 'llm_audit' | 'both'} DetectionSource
 *
 * @typedef {'VALIDATION_ERROR' | 'RATE_LIMITED' | 'INTERNAL_ERROR'} TopLevelErrorCode
 *
 * @typedef {'TIMEOUT' | 'RATE_LIMITED' | 'TOOL_ERROR'} ChannelErrorCode
 */

/**
 * @typedef {Object} GenerateRequest
 * @property {BrandId} brandId
 * @property {string} productName
 * @property {string} [coreActives]   - optional, comma-separated
 * @property {string} brief           - backend cap 800–1000 chars; UX nudges ~4–5 sentences
 * @property {Channel[]} channels     - 1–3 channels; fixed display order: tiktok → instagram → email
 */

/**
 * @typedef {Object} ChannelError
 * @property {ChannelErrorCode} code
 * @property {string} message
 */

/**
 * @typedef {Object} TopLevelError
 * @property {TopLevelErrorCode} code
 * @property {string} message
 * @property {string} [detail]
 */

/**
 * All fields are always present. Fields that don't apply are null, never omitted.
 * Check generation_status first — it determines how to read the rest.
 *
 * @typedef {Object} ChannelResult
 * @property {Channel} channel
 * @property {GenerationStatus} generation_status     - check this first
 * @property {string | null} raw_draft                - null if generation_status === 'error'
 * @property {ComplianceStatus | null} compliance_status  - null if error
 * @property {string[] | null} flagged_phrases        - [] if PASSED; null if error
 * @property {string | null} explanation              - "" if PASSED; null if error
 * @property {DetectionSource | null} detection_source - null if PASSED or error
 * @property {string | null} final_safe_output        - exact copy of raw_draft if PASSED; null if error; NO disclosure tag appended
 * @property {boolean | null} retry_exhausted         - true only if FAILED after iteration limit; null if error
 * @property {ChannelError | null} error              - {code, message} if error; null if completed
 */

/**
 * @typedef {Object} GenerateResponse
 * @property {ChannelResult[]} results  - 1–3 items; order matches requested channels
 * @property {TopLevelError | null} error  - null on success; populated on pre-dispatch failure (results: [])
 */

/** Fixed display order for result cards, regardless of selection order. */
export const CHANNEL_DISPLAY_ORDER = /** @type {Channel[]} */ (['tiktok', 'instagram', 'email'])

export const BRANDS = /** @type {{ id: BrandId; label: string }[]} */ ([
  { id: 'tower_28', label: 'Tower 28' },
  { id: 'half_magic', label: 'Half Magic' },
])
