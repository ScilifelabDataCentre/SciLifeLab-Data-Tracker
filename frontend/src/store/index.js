import Vue from 'vue'
import Vuex from 'vuex'

import adminUsers from './adminUsers'
import collections from './collections'
import currentUser from './currentUser'
import datasets from './datasets'
import entries from './entries'

Vue.use(Vuex)

/*
 * If not building with SSR mode, you can
 * directly export the Store instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Store instance.
 */

export default function (/* { ssrContext } */) {
  const Store = new Vuex.Store({
    modules: {
      adminUsers,
      collections,
      currentUser,
      datasets,
      entries,
    },

    // enable strict mode (adds overhead!)
    // for dev mode only
    strict: process.env.DEV
  })

  return Store
}
