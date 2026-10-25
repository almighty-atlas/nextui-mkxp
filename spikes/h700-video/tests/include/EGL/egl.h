/* SPDX-License-Identifier: MIT -- original mock API surface; not production headers. */
#ifndef MOCK_EGL_H
#define MOCK_EGL_H
typedef void *EGLDisplay;
#define EGL_NO_DISPLAY ((EGLDisplay)0)
#define EGL_VENDOR 1
#define EGL_VERSION 2
EGLDisplay eglGetCurrentDisplay(void);
const char *eglQueryString(EGLDisplay,int);
#endif
