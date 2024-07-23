import pstats
import sys

#See https://alex-ber.medium.com/converting-prof-files-to-callgrind-f6ae56fae0d3 for more details.
def convert_prof_to_callgrind(input_file, output_file):
    # Load the profile statistics
    stats = pstats.Stats(input_file)

    with open(output_file, 'w') as f:
        f.write("events: ns\n")  # Use nanoseconds as the unit

        # Write function and caller statistics to the callgrind file
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            filename, line, name = func
            f.write(f"fl={filename}\n")
            f.write(f"fn={name}\n")
            f.write(f"{line} {ct}\n")  # Time is in the original units

            for caller, (cc, nc, tt, ct) in callers.items():
                c_filename, c_line, c_name = caller
                f.write(f"cfl={c_filename}\n")
                f.write(f"cfn={c_name}\n")
                f.write(f"calls={nc} {c_line}\n")
                f.write(f"{line} {ct}\n")  # Time is in the original units

            f.write("\n")


def main():
    if len(sys.argv) != 3:
        print("Usage: python prof_to_callgrind.py input.prof output.callgrind")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    convert_prof_to_callgrind(input_file, output_file)


if __name__ == "__main__":
    main()

# Usage note:
# The convert_prof_to_callgrind function converts .prof files to .callgrind format.
# To use the script, run: python prof_to_callgrind.py input.prof output.callgrind