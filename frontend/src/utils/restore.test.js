// node --test로 돌린다(npm test). backend/tests/test_reversible_masking.py와 같은 경우를 확인한다.
import assert from 'node:assert/strict'
import test from 'node:test'
import { redactResultForStorage, restorePlaceholders } from './restore.js'

const EMAIL = [{ placeholder: '[MASKED_EMAIL_1]', type: 'Email', original: 'minji.kim@naver.com' }]
const PHONE = [{ placeholder: '[MASKED_PHONE_1]', type: 'Phone', original: '010-1111-2222' }]

test('restores bracketed and bare placeholders, including a Korean particle after a bare one', () => {
  const { text, count } = restorePlaceholders('MASKED_EMAIL_1로 회신하고 [MASKED_EMAIL_1] 확인', EMAIL)
  assert.equal(text, 'minji.kim@naver.com로 회신하고 minji.kim@naver.com 확인')
  assert.equal(count, 2)
})

test('does not touch longer placeholder names', () => {
  const { text, count } = restorePlaceholders('[MASKED_PHONE_10], MASKED_PHONE_12 와 [MASKED_PHONE_1]', PHONE)
  assert.equal(text, '[MASKED_PHONE_10], MASKED_PHONE_12 와 010-1111-2222')
  assert.equal(count, 1)
})

test('inserts original values literally', () => {
  const entries = [{ placeholder: '[MASKED_PASSWORD_1]', type: 'Password', original: 'a$&b$1' }]
  assert.equal(restorePlaceholders('pw=[MASKED_PASSWORD_1]', entries).text, 'pw=a$&b$1')
})

test('stored results keep no original values', () => {
  const result = {
    masked_text: '연락처 [MASKED_PHONE_1]',
    findings: [{ type: 'Phone', value: '010-1111-2222', exact_quote: '010-1111-2222', masked_value: '[MASKED_PHONE_1]' }],
    placeholders: PHONE,
  }
  const stored = redactResultForStorage(result)
  assert.equal(JSON.stringify(stored).includes('010-1111-2222'), false)
  assert.equal(stored.placeholders_dropped, 1)
  assert.equal(stored.findings[0].value, '[MASKED_PHONE_1]')
})
