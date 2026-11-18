import { createRouter, createWebHistory } from 'vue-router'
import type { RouteLocationNormalized } from 'vue-router'
import type { useAuthStore } from './stores/auth'

export type ViewName = 'today' | 'plan' | 'stats' | 'admin' | 'settings'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/today' },
    { path: '/login', name: 'login', component: () => import('./views/Login.vue') },
    { path: '/today', name: 'today', component: () => import('./views/Today.vue') },
    { path: '/plan', name: 'plan', component: () => import('./views/Plan.vue') },
    { path: '/stats', name: 'stats', component: () => import('./views/Stats.vue') },
    { path: '/admin', name: 'admin', meta: { requiresAdmin: true }, component: () => import('./views/Admin.vue') },
    { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/today' }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

export function loginDestination(to: RouteLocationNormalized, isSuperadmin: boolean) {
  const target = to.query.next
  if (typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')) {
    const resolved = router.resolve(target)
    if (resolved.name && resolved.name !== 'login' && (!resolved.meta.requiresAdmin || isSuperadmin)) {
      return { path: resolved.path, query: resolved.query, hash: resolved.hash, replace: true }
    }
  }
  return { name: 'today', replace: true }
}

export function guardRoutes(auth: ReturnType<typeof useAuthStore>) {
  const restored = auth.restore()
  router.beforeEach(async (to) => {
    await restored
    if (to.name === 'login') {
      if (auth.isLoggedIn) return loginDestination(to, auth.isSuperadmin)
    } else if (!auth.isLoggedIn) {
      return { name: 'login', query: { next: to.fullPath }, replace: true }
    } else if (to.meta.requiresAdmin && !auth.isSuperadmin) {
      return { name: 'today', replace: true }
    }
  })
}
