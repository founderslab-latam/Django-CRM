import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import {
  getMacros,
  createMacro,
  updateMacro,
  deleteMacro,
  activateMacro
} from '$lib/server/v2/macros.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  return getMacros({ cookies });
}

// `is_active` is deliberately not read here: the create/edit form has no
// control for it (see the page's `fields` snippet), so a macro write from
// this form never carries it. That closes the gap "Turn off"'s two-click
// `ConfirmAction` used to have a sibling: unchecking a box in the edit panel
// and hitting Save used to flip `is_active` with no confirm and none of the
// consequence copy the dedicated action carries. Turning a macro back on now
// only happens through the `activate` action below, which sends nothing but
// the id and `is_active: true`.
/** @param {FormData} form */
function readValues(form) {
  return {
    title: form.get('title')?.toString() ?? '',
    body: form.get('body')?.toString() ?? '',
    scope: form.get('scope')?.toString() ?? ''
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  // Every signed-in member may create their own personal macro here.
  // `can_create_org` only decides whether the form offers `scope=org` at
  // all; `_resolve_scope_and_owner` re-derives admin status server-side and
  // is what actually turns a non-admin's org-scope attempt into 403.
  async create(event) {
    const form = await event.request.formData();
    const values = readValues(form);
    try {
      await createMacro(event, values);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, {
          create: { error: get(_)('settings.macros.error_create_forbidden') }
        });
      }
      return fail(400, {
        create: { error: readableError(err, get(_)('settings.macros.error_create_fallback')) }
      });
    }
    return { created: true };
  },

  async update(event) {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    const values = readValues(form);
    try {
      await updateMacro(event, id, values);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, {
          update: { error: get(_)('settings.macros.error_update_forbidden') }
        });
      }
      if (err?.status === 404) {
        // A personal macro belonging to someone else answers 404 on purpose:
        // a 403 would confirm the row exists. Say the same thing back.
        return fail(404, { update: { error: get(_)('settings.macros.error_update_not_yours') } });
      }
      return fail(400, {
        update: { error: readableError(err, get(_)('settings.macros.error_update_fallback')) }
      });
    }
    return { updated: true };
  },

  async delete(event) {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    try {
      await deleteMacro(event, id);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, {
          delete: { error: get(_)('settings.macros.error_delete_forbidden') }
        });
      }
      if (err?.status === 404) {
        // Same reasoning as `update`: the row not being yours reads the same
        // as the row not existing, on purpose.
        return fail(404, { delete: { error: get(_)('settings.macros.error_delete_not_yours') } });
      }
      return fail(400, {
        delete: { error: readableError(err, get(_)('settings.macros.error_delete_fallback')) }
      });
    }
    return { deleted: true };
  },

  // A macro's own action, not a reuse of `update`. `readValues` builds a
  // full macro payload from the form, and this control only ever submits an
  // id: posting through `update` would read `title`/`body` back as `''`
  // (FormData has no key for either, `readValues` falls back to an empty
  // string) and `buildBody` would then throw ("A macro needs a title.")
  // before a request was even made. Calling `activateMacro` sidesteps
  // `readValues`/`buildBody` entirely, so the PATCH body is
  // `{ is_active: true }` and nothing else.
  async activate(event) {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    try {
      await activateMacro(event, id);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, {
          activate: { error: get(_)('settings.macros.error_activate_forbidden') }
        });
      }
      if (err?.status === 404) {
        // Same reasoning as `update`/`delete`: the row not being yours reads
        // the same as the row not existing, on purpose.
        return fail(404, {
          activate: { error: get(_)('settings.macros.error_activate_not_yours') }
        });
      }
      return fail(400, {
        activate: { error: readableError(err, get(_)('settings.macros.error_activate_fallback')) }
      });
    }
    return { activated: true };
  }
};
