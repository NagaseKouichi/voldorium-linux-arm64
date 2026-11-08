/* Synthetic, game-independent host FP mode regression tests. */
#include "sh4rt.h"
#include <assert.h>
#include <stdio.h>

__attribute__((noinline)) static float add(float a, float b) { return a + b; }
__attribute__((noinline)) static float mul(float a, float b) { return a * b; }
__attribute__((noinline)) static double dadd(double a, double b) { return a + b; }
__attribute__((noinline)) static double dmul(double a, double b) { return a * b; }
static u64 d2u(double d) { u64 u; memcpy(&u, &d, 8); return u; }
static double u2d(u64 u) { double d; memcpy(&d, &u, 8); return d; }
static unsigned long read_mode(void)
{
#if defined(__aarch64__)
    unsigned long v; __asm__ volatile("mrs %0, fpcr" : "=r"(v)); return v;
#else
    return _mm_getcsr();
#endif
}
int main(void)
{
    for (u32 dn = 0; dn < 2; dn++) for (u32 rm = 0; rm < 4; rm++) {
        /* Start with hostile rounding, default-NaN, denormal and sticky modes. */
#if defined(__aarch64__)
        u64 dirty = (1ull << 25) | (1ull << 24) | (1ull << 22);
        u64 sticky = 0x9f;
        __asm__ volatile("msr fpcr, %0\n\tmsr fpsr, %1" : : "r"(dirty), "r"(sticky) : "memory");
#else
        _mm_setcsr(0x1f80 | (1u << 13) | (1u << 15) | (1u << 6) | 0x3f);
#endif
        sh4_set_host_fpmode((dn << 18) | rm);
#if defined(__aarch64__)
        assert(read_mode() == ((rm == 1 ? 3ul << 22 : 0) | (dn << 24)));
        u64 status; __asm__ volatile("mrs %0, fpsr" : "=r"(status));
        assert(status == 0);
#else
        assert(read_mode() == (0x1f80u | (rm == 1 ? 3u << 13 : 0) | (dn << 15)));
#endif
        /* 3/4 ulp distinguishes nearest from truncation, both signs. */
        assert(f2u(add(1.f, u2f(0x33c00000))) == (rm == 1 ? 0x3f800000u : 0x3f800001u));
        assert(f2u(add(-1.f, -u2f(0x33c00000))) == (rm == 1 ? 0xbf800000u : 0xbf800001u));
        assert(f2u(mul(u2f(0x00800000), 0.5f)) == (dn ? 0u : 0x00400000u));
        assert(f2u(mul(u2f(0x80800000), 0.5f)) == (dn ? 0x80000000u : 0x80400000u));
        assert(d2u(dadd(1., 0x1.8p-53)) == (rm == 1 ? 0x3ff0000000000000ull : 0x3ff0000000000001ull));
        assert(d2u(dadd(-1., -0x1.8p-53)) == (rm == 1 ? 0xbff0000000000000ull : 0xbff0000000000001ull));
        assert(d2u(dmul(u2d(0x0010000000000000ull), 0.5)) == (dn ? 0ull : 0x0008000000000000ull));
        assert(d2u(dmul(u2d(0x8010000000000000ull), 0.5)) == (dn ? 0x8000000000000000ull : 0x8008000000000000ull));
        assert(d2u(dadd(u2d(0x7ff8123456789abcull), 1.)) == 0x7ff8123456789abcull);
        /* ARM FZ flushes inputs too; existing SSE deliberately leaves DAZ off. */
#if defined(__aarch64__)
        assert(f2u(mul(u2f(0x00400000), 4.f)) == (dn ? 0u : 0x01000000u));
#else
        assert(f2u(mul(u2f(0x00400000), 4.f)) == 0x01000000u);
#endif
        /* Do not confuse the guest denormal bit with ARM default-NaN. */
        assert(f2u(add(u2f(0x7fc12345), 1.f)) == 0x7fc12345u);
    }
    SH4 c = {0}; c.fr[0] = 1.f; c.xf[0] = 2.f;
    sh4_set_fpscr(&c, (1u << 21) | 1u);
    assert(c.fr[0] == 2.f && c.xf[0] == 1.f && c.fpscr == ((1u << 21) | 1u));
    sh4_set_host_fpmode(0);
    puts("PASS: float/double RM=0..3, FTZ, signed underflow, input denormals, NaN payload, bank swap/control+status reset");
    return 0;
}
