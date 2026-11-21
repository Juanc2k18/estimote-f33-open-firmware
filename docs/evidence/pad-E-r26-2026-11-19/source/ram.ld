ENTRY(_start)
MEMORY { RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 0x8000 }
SECTIONS {
  .text : { KEEP(*(.entry)) *(.text*) *(.rodata*) } > RAM
  .data : { *(.data*) } > RAM
  .bss (NOLOAD) : { *(.bss*) *(COMMON) } > RAM
  .results 0x20006000 (NOLOAD) : { *(.results) } > RAM
}
