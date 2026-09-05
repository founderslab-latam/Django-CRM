import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { getTags, createTag, archiveTag, restoreTag, mergeTags } from '$lib/server/v2/tags.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  return getTags({ cookies });
}

/** @type {import('./$types').Actions} */
export const actions = {
  // Admin-only. `load`'s `can_edit` hides the "New tag" control for a member,
  // but that is only the affordance; this check is the one that matters.
  // `TagsListView.post` (`backend/common/views/tags_views.py:143-149`) 403s a
  // non-admin regardless of what reaches it, so this branch exists to turn
  // that response into a message instead of a raw backend error string, not
  // to be the authority itself.
  async create(event) {
    const form = await event.request.formData();
    const name = form.get('name')?.toString() ?? '';

    try {
      await createTag(event, { name });
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, {
          create: { name, error: get(_)('settings.tags.error_create_forbidden') }
        });
      }
      return fail(400, {
        create: { name, error: readableError(err, get(_)('settings.tags.error_create_fallback')) }
      });
    }

    // No redirect. The list is on this page, and `load` re-runs after an
    // action, so the new tag appears where the user is already looking.
    return { created: true };
  },

  // Turns a tag off. Admin-only on the backend (`TagsDetailView.delete`),
  // same split as `create`: `can_edit` hides the control for a member, this
  // branch is what actually matters if that hint is bypassed. The backend
  // soft-archives (`is_active = False`); it never deletes the row, so the
  // error copy below stays consistent with that, nothing here talks about
  // removal.
  async archive(event) {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    if (!id) return fail(400, { archive: { error: get(_)('settings.tags.error_no_id') } });

    try {
      await archiveTag(event, id);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, { archive: { error: get(_)('settings.tags.error_archive_forbidden') } });
      }
      return fail(400, {
        archive: { error: readableError(err, get(_)('settings.tags.error_archive_fallback')) }
      });
    }
    return { archived: true };
  },

  // Turns an archived tag back on. Same admin-only gate as `archive`.
  async restore(event) {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    if (!id) return fail(400, { restore: { error: get(_)('settings.tags.error_no_id') } });

    try {
      await restoreTag(event, id);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, { restore: { error: get(_)('settings.tags.error_restore_forbidden') } });
      }
      return fail(400, {
        restore: { error: readableError(err, get(_)('settings.tags.error_restore_fallback')) }
      });
    }
    return { restored: true };
  },

  // Moves every record off one tag and onto another, then archives the one it
  // emptied. Same admin-only split as the three above: `can_edit` decides
  // whether the button renders, `TagsMergeView` decides whether it works.
  //
  // Both ids come off the form, and neither is trusted here. The backend
  // resolves each inside the caller's org, which is what stops an `into` from
  // another tenant, so this branch only turns the refusal into copy.
  async merge(event) {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    const into = form.get('into')?.toString() ?? '';
    if (!id || !into) {
      return fail(400, { merge: { error: get(_)('settings.tags.error_merge_no_id') } });
    }

    let result;
    try {
      result = await mergeTags(event, id, into);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, { merge: { error: get(_)('settings.tags.error_merge_forbidden') } });
      }
      return fail(400, {
        merge: { error: readableError(err, get(_)('settings.tags.error_merge_fallback')) }
      });
    }

    // `moved` is the whole point of reporting anything back: a merge that
    // moved nothing looks identical to one that moved two hundred records,
    // and the second is the one an admin wants to have seen before they close
    // the page.
    return {
      merged: {
        name: result.tag?.name ?? '',
        moved: result.moved
      }
    };
  }
};
