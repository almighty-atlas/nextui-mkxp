/* SPDX-License-Identifier: MIT
 * Linux child-process supervisor; optional passive evdev chord, never EVIOCGRAB.
 * Original implementation; no upstream port code or SDL state modifications.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t requested;
static void request_stop(int sig) { requested = sig; }
static long long now_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) _exit(125);
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}
static int number(const char *s, int low, int high) {
    char *end;
    errno = 0;
    long value = strtol(s, &end, 10);
    if (errno || !*s || *end || value < low || value > high) return -1;
    return (int)value;
}
static int fail(const char *code) { fprintf(stderr, "RMXP_SUPERVISOR_ERROR=%s\n", code); return 125; }

struct chord { int first, second, mask; bool armed, dropped; long long since; };
static void reset_chord(struct chord *c, int fd) {
    unsigned char bits[(KEY_MAX + 8) / 8] = {0};
    c->mask = 3; /* fail closed until releases when state cannot be queried */
    if (ioctl(fd, EVIOCGKEY(sizeof(bits)), bits) >= 0)
        c->mask = (!!(bits[c->first / 8] & (1U << (c->first % 8)))) |
                  ((!!(bits[c->second / 8] & (1U << (c->second % 8)))) << 1);
    c->armed = c->mask == 0;
    c->since = -1;
}
static void event(struct chord *c, const struct input_event *e, int fd) {
    if (e->type == EV_SYN && e->code == SYN_DROPPED) {
        c->dropped = true; c->armed = false; c->since = -1;
        return;
    }
    if (c->dropped) {
        if (e->type == EV_SYN && e->code == SYN_REPORT) {
            c->dropped = false; reset_chord(c, fd);
        }
        return;
    }
    if (e->type != EV_KEY || (e->value != 0 && e->value != 1)) return;
    int bit = e->code == c->first ? 1 : e->code == c->second ? 2 : 0;
    if (e->value) c->mask |= bit; else c->mask &= ~bit;
    if (!c->mask) c->armed = true;
    if (c->mask != 3) c->since = -1;
}

int main(int argc, char **argv) {
    const char *input = NULL;
    int hold_ms = 1500, grace_ms = 3000, fd = -1, arg = 1;
    struct chord chord = {.first = -1, .second = -1, .since = -1};
#ifdef RMXP_TEST_INPUT
    bool test_input = false;
#endif
    for (; arg < argc && strcmp(argv[arg], "--"); arg++) {
        if (!strcmp(argv[arg], "--input") && arg + 1 < argc) input = argv[++arg];
        else if (!strcmp(argv[arg], "--keys") && arg + 2 < argc) {
            chord.first = number(argv[++arg], 0, KEY_MAX);
            chord.second = number(argv[++arg], 0, KEY_MAX);
            if (chord.first < 0 || chord.second < 0 || chord.first == chord.second) return fail("KEYS");
        } else if (!strcmp(argv[arg], "--hold-ms") && arg + 1 < argc) {
            hold_ms = number(argv[++arg], 500, 5000);
            if (hold_ms < 0) return fail("HOLD_RANGE");
        } else if (!strcmp(argv[arg], "--grace-ms") && arg + 1 < argc) {
            grace_ms = number(argv[++arg], 100, 10000);
            if (grace_ms < 0) return fail("GRACE_RANGE");
#ifdef RMXP_TEST_INPUT
        } else if (!strcmp(argv[arg], "--test-fd") && arg + 1 < argc) {
            fd = number(argv[++arg], 0, 1024); test_input = true;
            if (fd < 0) return fail("TEST_FD");
#endif
        } else return fail("ARGUMENTS");
    }
    if (arg + 1 >= argc) return fail("COMMAND_REQUIRED");
    if (input) {
        if (fd >= 0) return fail("INPUT_CONFLICT");
        fd = open(input, O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
        struct stat st;
        int version;
        if (fd < 0 || fstat(fd, &st) || !S_ISCHR(st.st_mode) || ioctl(fd, EVIOCGVERSION, &version) < 0)
            return fail("EVDEV_REQUIRED");
    }
    if ((fd >= 0) != (chord.first >= 0)) return fail("INPUT_AND_KEYS_REQUIRED");
    if (fd >= 0) {
        if (fcntl(fd, F_SETFL, O_NONBLOCK) < 0 || fcntl(fd, F_SETFD, FD_CLOEXEC) < 0) return fail("INPUT_FLAGS");
#ifdef RMXP_TEST_INPUT
        if (test_input) { chord.armed = false; chord.mask = 3; }
        else
#endif
        {
            unsigned char supported[(KEY_MAX + 8) / 8] = {0};
            if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof(supported)), supported) < 0 ||
                !(supported[chord.first / 8] & (1U << (chord.first % 8))) ||
                !(supported[chord.second / 8] & (1U << (chord.second % 8)))) return fail("KEYS_UNSUPPORTED");
            reset_chord(&chord, fd);
        }
    }
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = request_stop;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, NULL) || sigaction(SIGINT, &action, NULL) || sigaction(SIGHUP, &action, NULL))
        return fail("SIGNALS");
    if (prctl(PR_SET_CHILD_SUBREAPER, 1) < 0) return fail("SUBREAPER");
    pid_t parent = getpid();
    pid_t child = fork();
    if (child < 0) return fail("FORK");
    if (child == 0) {
        if (setpgid(0, 0) || prctl(PR_SET_PDEATHSIG, SIGKILL) || getppid() != parent) _exit(125);
        struct rlimit no_core = {0, 0};
        if (setrlimit(RLIMIT_CORE, &no_core)) _exit(125);
        signal(SIGTERM, SIG_DFL); signal(SIGINT, SIG_DFL); signal(SIGHUP, SIG_DFL);
        if (fd >= 0) close(fd);
        execvp(argv[arg + 1], &argv[arg + 1]);
        _exit(127);
    }
    /* Both sides establish the group before exec/signal handling. */
    if (setpgid(child, child) < 0 && errno != EACCES && errno != ESRCH) {
        kill(child, SIGKILL); waitpid(child, NULL, 0); return fail("PROCESS_GROUP");
    }
    const char *reason = "natural";
    long long deadline = -1;
    bool escalated = false;
    siginfo_t result;
    fprintf(stderr, "RMXP_SESSION=started\n");
    for (;;) {
        memset(&result, 0, sizeof(result));
        if (waitid(P_PID, (id_t)child, &result, WEXITED | WNOHANG | WNOWAIT) < 0 && errno != EINTR) {
            kill(-child, SIGKILL); waitpid(child, NULL, 0); return fail("WAIT");
        }
        if (result.si_pid == child) break;
        struct pollfd poll_input = {.fd = fd, .events = POLLIN};
        int ready = poll(&poll_input, fd >= 0 ? 1 : 0, 20);
        if (ready > 0 && fd >= 0) {
            struct input_event events[32];
            ssize_t bytes;
            int batches = 0;
            /* Drain queued releases before deciding whether the hold completed. */
            while (batches++ < 64 && (bytes = read(fd, events, sizeof(events))) > 0 && bytes % (ssize_t)sizeof(events[0]) == 0) {
                for (size_t i = 0; i < (size_t)bytes / sizeof(events[0]); i++) event(&chord, &events[i], fd);
            }
            if (bytes == 0 || bytes > 0 || (errno != EAGAIN && errno != EINTR)) {
                close(fd); fd = -1; chord.armed = false;
                fprintf(stderr, "RMXP_INPUT=lost\n");
            }
        }
        long long now = now_ms();
        if (deadline < 0 && requested) { reason = "supervisor_signal"; deadline = now + grace_ms; }
        if (deadline < 0 && fd >= 0 && chord.armed && !chord.dropped && chord.mask == 3) {
            if (chord.since < 0) chord.since = now;
            if (now - chord.since >= hold_ms) { reason = "chord"; deadline = now + grace_ms; }
        }
        if (deadline >= 0 && !escalated) {
            if (now >= deadline) {
                kill(-child, SIGKILL); escalated = true;
                fprintf(stderr, "RMXP_STOP=kill\n");
            } else {
                /* Send TERM only once, not on every poll. */
                static bool term_sent;
                if (!term_sent) { kill(-child, SIGTERM); term_sent = true; fprintf(stderr, "RMXP_STOP=term\n"); }
            }
        }
    }
    if (fd >= 0) close(fd);
    /* Keep the leader unreaped until signalling its group is complete: no PID reuse. */
    kill(-child, SIGTERM);
    long long cleanup_until = now_ms() + 100;
    while (now_ms() < cleanup_until) poll(NULL, 0, 10);
    kill(-child, SIGKILL);
    int status;
    while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    long long reap_until = now_ms() + 200;
    for (;;) {
        pid_t reaped = waitpid(-1, NULL, WNOHANG);
        if (reaped > 0) continue;
        if ((reaped < 0 && errno == ECHILD) || now_ms() >= reap_until) break;
        poll(NULL, 0, 10);
    }
    if (result.si_code == CLD_EXITED) {
        fprintf(stderr, "RMXP_RESULT=exit CODE=%d REASON=%s\n", result.si_status, reason);
        return result.si_status;
    }
    fprintf(stderr, "RMXP_RESULT=signal SIGNAL=%d REASON=%s\n", result.si_status, reason);
    return 128 + result.si_status;
}
