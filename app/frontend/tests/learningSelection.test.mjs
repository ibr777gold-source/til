import test from 'node:test';
import assert from 'node:assert/strict';
import {chooseNext} from '../src/learningSelection.ts';

test('resumes the selected course, including an unpublished saved lesson',()=>{
  const lessons=[{id:'one'},{id:'two'}];
  assert.deepEqual(chooseNext('uz-ru',lessons,[],[{lesson_id:'other',course:'ru-uz'},{lesson_id:'withdrawn',course:'uz-ru'}]),{id:'withdrawn',resuming:true});
});
test('chooses the first unfinished lesson in course order and handles empty courses',()=>{
  const lessons=[{id:'one'},{id:'two'}];
  assert.deepEqual(chooseNext('uz-ru',lessons,[{lesson_id:'one',completed:true}],[]),{id:'two',resuming:false});
  assert.deepEqual(chooseNext('uz-ru',lessons,[{lesson_id:'one',completed:true},{lesson_id:'two',completed:true}],[]),{id:'one',resuming:false});
  assert.equal(chooseNext('uz-ru',[],[],[]),null);
});
