import struct

def get_fat_partition_offset(image_file):
    mbr = open(image_file, 'rb').read()
    partition_table = mbr[446:510]
    signature = struct.unpack('<H', mbr[510:512])[0]
    little_endian = (signature == 0xaa55) # should be True
    print("Little endian:", little_endian)
    PART_FMT = (little_endian and '<' or '>') + (
    "B"  # status (0x80 = bootable (active), 0x00 = non-bootable)
        # CHS of first block
    "B"  # Head
    "B"  # Sector is in bits 5; bits 9 of cylinder are in bits 7-6
    "B"  # bits 7-0 of cylinder
    "B"  # partition type
        # CHS of last block
    "B"  # Head
    "B"  # Sector is in bits 5; bits 9 of cylinder are in bits 7-6
    "B"  # bits 7-0 of cylinder
    "L"  # LBA of first sector in the partition
    "L"  # number of blocks in partition, in little-endian format
    )
    PART_SIZE = 16
    fmt_size = struct.calcsize(PART_FMT)
    # sanity check expectations
    assert fmt_size == PART_SIZE, \
    "Partition format string is %i bytes, not %i" % (
    fmt_size, PART_SIZE)

    def cyl_sector(sector_cyl, cylinder7_0):
        sector = sector_cyl & 0x1F # bits 5-0

        # bits 7-6 of sector_cyl contain bits 9-8 of the cylinder
        cyl_high = (sector_cyl >> 5) & 0x03
        cyl = (cyl_high << 8) | cylinder7_0
        return sector, cyl

    for partition in range(4):
        print("Partition #%i" % partition, end=' ')
        offset = PART_SIZE * partition
        (
            status,
            start_head, start_sector_cyl, start_cyl7_0,
            part_type,
            end_head, end_sector_cyl, end_cyl7_0,
            lba,
            blocks
            ) = struct.unpack(
            PART_FMT,
            partition_table[offset:offset + PART_SIZE]
            )
        if status == 0x80:
            print("Bootable", end=' ')
        elif status:
            print("Unknown status [%s]" % hex(status), end=' ')
        print("Type=0x%x" % part_type)
        start = (start_head,) + cyl_sector(
            start_sector_cyl, start_cyl7_0)
        end = (end_head,) + cyl_sector(
            end_sector_cyl, end_cyl7_0)
        print(" (Start: Heads:%i\tCyl:%i\tSect:%i)" % start)
        print(" (End:   Heads:%i\tCyl:%i\tSect:%i)" % end)
        print(" LBA:", lba)
        print(" Blocks:", blocks)
        if part_type==0x0c:
            return lba*512


