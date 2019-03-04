import asyncio
import aiohttp
import logging
import os
import sys
import getopt


async def check_cert(q_main, q_good, q_bad):
    while True:
        hostname = await q_main.get()

        conn = aiohttp.TCPConnector()
        session = aiohttp.ClientSession(connector=conn)

        success = False

        try:
            await session.get(hostname)
            success = True
        except aiohttp.ClientConnectorCertificateError as e:
            pass
        except aiohttp.ClientConnectorSSLError as e:
            pass 
        except Exception as e:
            # print("({}) bad hostname ?".format(hostname))
            pass

        await session.close()

        if success:
            await q_good.put(hostname)        
        else:
            await q_bad.put(hostname)

        q_main.task_done()


async def read_file(filename, q):
    with open(filename, "r") as f:
        for line in f:
            h_s = line.strip().split("://")
            h = "https://" + h_s[len(h_s) - 1]
            # print(" read : " + h +"\n", h)
            await q.put(h)


async def write_output_file(file, queue):
        while True:
            line = await queue.get()
            file.write(line + os.linesep); file.flush()
            queue.task_done()


async def main(argv):
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)

    filename = "urls"
    filename_good_urls = "Valid"
    filename_bad_urls = "Unvalid"

    jobs = 4

    if(len(argv) > 1):
        try:
            opts, args = getopt.getopt(argv[1::], "hi:j:", ["input=", "jobs="])
        except getopt.GetoptError:
            print("./" + argv[0] + " -i <inputfile> -j <jobs>")
            sys.exit(2)
        
        for opt, arg in opts:
            if opt == '-h':
                print("./" + argv[0] + " -i <inputfile> -j <jobs>")
                sys.exit(0)
            
            if opt in ("-i", "--input"):
                filename = arg
            
            if opt in ("-j", "--jobs"):
                jobs = int(arg)
    
    queue_from_file = asyncio.Queue(jobs + 1)
    queue_cert_good = asyncio.Queue(jobs)
    queue_cert_bad = asyncio.Queue(jobs)
    
    workers = []
    for i in range(jobs):
        workers.append(asyncio.create_task(
            check_cert(queue_from_file, queue_cert_good, queue_cert_bad)))
    
    try:
        f_good = open(filename_good_urls, "w")
        f_bad = open(filename_bad_urls, "w")
    except:
        print("Cannot open output files.")
        sys.exit(-1)

    t_wr_good = asyncio.create_task(write_output_file(f_good, queue_cert_good))
    t_wr_bad = asyncio.create_task(write_output_file(f_bad, queue_cert_bad))

    await asyncio.gather(asyncio.create_task(
        read_file(filename, queue_from_file)))

    await queue_from_file.join()
    await queue_cert_good.join()
    await queue_cert_bad.join()

    for worker in workers:
        worker.cancel()

    t_wr_bad.cancel()
    t_wr_good.cancel()

    print("Done")


if __name__ == '__main__':
    asyncio.run(main(sys.argv), debug=False)
